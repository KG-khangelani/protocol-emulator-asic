# SPDX-License-Identifier: Apache-2.0
"""MicroPython payload for the user's serial terminal on the TTDBv3 RP2350."""

import binascii
import gc
import json
import machine
import micropython
import rp2
import time
from machine import Pin
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode
from ttboard.util.platform import rp2350 as io


def record(**fields):
    print('UARTLAB ' + json.dumps(fields))


@rp2.asm_pio(out_init=rp2.PIO.OUT_HIGH, sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def wire_pair():
    # GPIO16 supplies the project clock and GPIO26 drives the FPGA's physical RX pin.
    pull(block).side(0)
    mov(isr, osr).side(0)
    pull(block).side(0)
    set(y, 20).side(0)  # Two 10-bit frames, then one idle mark.
    set(x, 15).side(0)
    label('arm')
    nop().side(0)
    jmp(x_dec, 'arm').side(1)
    label('bit')
    out(pins, 1).side(0)
    mov(x, isr).side(1)
    label('hold')
    nop().side(0)
    jmp(x_dec, 'hold').side(1)
    nop().side(0)
    jmp(y_dec, 'bit').side(1)
    label('idle')
    nop().side(0)
    jmp('idle').side(1)


@rp2.asm_pio()
def count_clock():
    # Observe the GPIO16 pad using a second machine running at the system clock.
    pull(block)
    mov(x, osr)
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    label('edge')
    wait(0, gpio, 16)
    wait(1, gpio, 16)
    jmp(x_dec, 'edge')
    push(block)


def bias_read():
    # Only MCU weak pulls are applied. The push-pull driver stays disabled.
    rx = Pin(26, Pin.IN, Pin.PULL_DOWN)
    time.sleep_us(250)
    down = rx.value()
    rx.init(Pin.IN, Pin.PULL_UP)
    time.sleep_us(250)
    up = rx.value()
    rx.init(Pin.IN, None)
    return [down, up]


def select(value):
    io.write_ui_in_byte(value)
    time.sleep_us(3)
    if io.read_ui_in_byte() != value:
        raise ValueError('physical selector failed', value, io.read_ui_in_byte())


@micropython.viper
def page(value: int) -> int:
    # TTDBv3 uses GPIO17..24 for UI and GPIO33..40 for UO. These are the
    # same SIO offsets as the public SDK. Wait four 1-us timer transitions
    # after the selector write, giving at least 3 us of settling.
    sio = ptr32(0xd0000000)
    timer = ptr32(0x400b0000)
    sio[10] = (sio[4] ^ (value << 17)) & (255 << 17)
    start = uint(timer[10])
    while uint(timer[10] - start) < uint(4):
        pass
    return (sio[2] >> 1) & 255


def park():
    io.write_uio_outputenable(0)
    Pin(26, Pin.IN, None)
    Pin(16, Pin.OUT, value=0)
    io.write_ui_in_byte(0xe7)
    tt.reset_project(True)


def cold(name, damaged):
    tt.clock_project_stop()
    tt.mode = RPMode.ASIC_RP_CONTROL
    park()
    readback = bytearray()
    registers = []
    biases = {}
    previous_reset = -1
    for edge, (selector, rst_n, write_data, expected_status, expected_bus) in enumerate(STEPS, 1):
        if edge < 76:
            io.write_uio_outputenable(0)
        select(selector)
        if rst_n != previous_reset:
            tt.reset_project(not rst_n)
            previous_reset = rst_n
        if write_data >= 0:
            assert selector & 0xc0 == 0xc0
            value = write_data ^ int(damaged and selector == 0xc1)
            io.write_uio_byte(value)
            io.write_uio_outputenable(255)
            assert io.read_uio_outputenable() == 255
        elif edge == 75:
            biases['released'] = bias_read()
            io.write_uio_byte(2)
            io.write_uio_outputenable(2)
        elif expected_bus >= 0:
            assert io.read_uio_outputenable() == 0
        time.sleep_us(3)
        io.write_clock(1)
        time.sleep_us(3)
        io.write_clock(0)
        time.sleep_us(3)
        if expected_status >= 0:
            actual = io.read_uo_out_byte()
            if actual != expected_status:
                raise ValueError('status', edge, selector, expected_status, actual)
        if expected_bus >= 0:
            observed = io.read_uio_byte()
            if observed != expected_bus:
                record(case=name, event='readback_failure', edge=edge, selector=selector,
                       expected=expected_bus, observed=observed)
                if damaged and edge == 38 and expected_bus == 0 and observed == 1:
                    return False
                raise ValueError('program or register readback', edge, expected_bus, observed)
            if selector < 0xa0:
                readback.append(observed)
            else:
                registers.append([selector, observed])
            if selector in (0x80, 0x81):
                biases['driven_high' if selector == 0x80 else 'driven_low'] = bias_read()
    assert not damaged and len(readback) == 32 and io.read_uio_outputenable() == 2
    select(0x67)
    identity = io.read_uo_out_byte()
    select(0)
    status = io.read_uo_out_byte()
    assert identity == 0x22 and status == 0x20
    record(case=name, event='cold', edges=len(STEPS), image=binascii.hexlify(readback).decode(),
           registers=registers, identity=identity, status=status, uio1_pull_down_up=biases)
    return True


def measure_clock(counter, hz):
    edges = 100000
    counter.active(1)
    before = time.ticks_us()
    counter.put(edges - 1)
    while not counter.rx_fifo():
        if time.ticks_diff(time.ticks_us(), before) > 250000:
            raise ValueError('clock pad counter timed out')
    elapsed = time.ticks_diff(time.ticks_us(), before)
    counter.get()
    counter.active(0)
    # Includes the time to queue the count and observe the FIFO flag.
    assert abs(elapsed - edges * 1000000 // hz) <= edges * 20000 // hz
    return elapsed


@micropython.native
def poll_pair(driver, read=page):
    ticks, diff = time.ticks_us, time.ticks_diff
    first_byte = None
    accepted = None
    terminal = None
    max_gap = max_duration = polls = 0
    start = last_poll = ticks()
    driver.active(1)
    while diff(ticks(), start) < 50000:
        at = ticks()
        gap = diff(at, last_poll)
        if gap > max_gap:
            max_gap = gap
        last_poll = at
        status = read(0)
        valid = read(0x63)
        if not status & 0x20:
            raise ValueError('program lost ready')
        if status >> 6 == 3:
            terminal = status
        elif status == 0xa7:
            if first_byte is None or not valid:
                raise ValueError('terminal without a first byte')
            second_byte = read(0x62)
            if read(0) != 0xa7 or read(0x63) != 1:
                raise ValueError('terminal changed during read')
            accepted = [first_byte, second_byte]
            terminal = status
        elif valid and first_byte is None:
            first_byte = read(0x62)
        polls += 1
        duration = diff(ticks(), at)
        if duration > max_duration:
            max_duration = duration
        if terminal is not None:
            break
    return terminal, first_byte, accepted, polls, max_gap, max_duration


def run_pair(name, hz, stop1, stop2, tx_id, count_id):
    first, second = (0x3c, 0xa5) if name == 'target-distinct' else (0x96, 0x69)
    bits = ((first << 1) | (stop1 << 9) | (second << 11) | (stop2 << 19) | (1 << 20))
    driver = rp2.StateMachine(tx_id, wire_pair, freq=2*hz, out_base=Pin(26), sideset_base=Pin(16))
    counter = rp2.StateMachine(count_id, count_clock, freq=-1)
    try:
        io.write_uio_outputenable(0)  # PIO now owns just the clock and the peer pad.
        driver.put(431)  # 1 + 432 + 1 rising edges per serial bit
        driver.put(bits)
        gc.collect()
        terminal, first_byte, accepted, polls, max_gap, max_duration = poll_pair(driver)
        # Two independent integer-us interval measurements may each truncate by <1 us.
        bound = max_gap + max_duration + 2
        elapsed = measure_clock(counter, hz)
        record(case=name, event='uart', configured_hz=hz, cpu_hz=machine.freq(), terminal=terminal,
               tentative=first_byte, accepted=accepted, polls=polls, max_poll_gap_us=max_gap,
               max_read_sequence_us=max_duration, service_upper_us=bound,
               pad_clock_periods=100000, pad_count_elapsed_us=elapsed)
        assert bound * hz < 4340 * 1000000
        if stop1 and stop2:
            assert terminal == 0xa7 and accepted == [first, second]
        else:
            assert terminal == 0xe6 and accepted is None
    finally:
        driver.active(0)
        counter.active(0)
        park()


tt = DemoBoard.get()


def delivery_trials(free):
    for name, hz, stop1, stop2 in (
            ('slow-good', 1000000, 1, 1), ('target-good', 12500000, 1, 1),
            ('target-bad-first', 12500000, 0, 1), ('target-bad-second', 12500000, 1, 0),
            ('target-distinct', 12500000, 1, 1), ('target-fresh', 12500000, 1, 1)):
        assert cold(name, False)
        run_pair(name, hz, stop1, stop2, free[0], free[1])


def run_suite(trials, programs, required_machines, cold_load=cold):
    original_frequency = machine.freq()
    original_mode = tt.mode
    record(event='controller', original_hz=original_frequency, mode=tt.mode_str)
    free = [index for index in range(4) if not rp2.StateMachine(index).active()]
    assert len(free) >= required_machines
    try:
        machine.freq(125000000)
        assert machine.freq() == 125000000
        assert not cold_load('damaged', True)
        trials(free)
    finally:
        park()
        try:
            for program in programs:
                rp2.PIO(0).remove_program(program)
        finally:
            machine.freq(original_frequency)
            tt.mode = original_mode
    record(status='PASS', restored_cpu_hz=machine.freq(), host_uio_oe=io.read_uio_outputenable())
