# SPDX-License-Identifier: Apache-2.0
"""MicroPython payload; no filesystem operations on the RP2350."""
import array
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


def report(**fields):
    print('SPILAB ' + json.dumps(fields))


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def core_clock():
    set(pins, 1) [4]
    set(pins, 0) [4]


@rp2.asm_pio(out_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH),
             out_shiftdir=rp2.PIO.SHIFT_RIGHT)
def requester():
    wait(1, gpio, 16)
    wrap_target()
    pull(block)
    out(pins, 3)
    out(x, 29)
    label('hold')
    jmp(x_dec, 'hold')
    wrap()


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def sampler():
    wait(1, gpio, 16)
    wrap_target()
    in_(pins, 8)
    wrap()


@micropython.viper
def pack_trace(buf, changes, count: int, capacity: int) -> int:
    # XOR only the periodic clock with its first ten sampled levels. Any
    # exceptions are encoded alongside all other pin changes, losslessly.
    src = ptr8(buf)
    dst = ptr8(changes)
    last = -1
    used = 0
    for i in range(count):
        value = (src[i] & 127) ^ (src[i % 10] & 64)
        if value != last:
            if used + 3 > capacity:
                return -1
            dst[used] = i & 255
            dst[used + 1] = i >> 8
            dst[used + 2] = value
            used += 3
            last = value
    return used


def pulse():
    io.write_clock(1)
    time.sleep_us(3)
    io.write_clock(0)
    time.sleep_us(3)


def load_program(damaged):
    Pin(32, Pin.OUT, value=0)
    io.write_uio_outputenable(0x80)
    run = Pin(32, Pin.OUT, value=0)
    stage = Pin(30, Pin.OUT, value=0)
    Pin(16, Pin.OUT, value=0)
    for i in range(17, 25):
        Pin(i, Pin.OUT, value=0)
    returned = bytearray()
    registers = []
    was_reset = -1
    for index in range(0, len(PLAN), 6):
        reset, select, value, flags, want_status, want_data = PLAN[index:index+6]
        if reset != was_reset:
            tt.reset_project(not reset)
            was_reset = reset
        if flags & 1:
            stage.value(1)
            io.write_ui_in_byte(value ^ int(damaged and index == 4*6))
            time.sleep_us(3)
            pulse()
            stage.value(0)
        io.write_ui_in_byte(0xe7 if flags & 8 else select)
        time.sleep_us(3)
        pulse()
        actual = io.read_uo_out_byte()
        if flags & 2 and actual != want_status:
            raise ValueError('loader status', index//6, select, want_status, actual)
        if flags & 4:
            if actual != want_data:
                report(event='readback_error', row=index//6, selector=select, expected=want_data, observed=actual)
                if damaged and select == 0x81 and actual == (want_data ^ 1):
                    return
                raise ValueError('loader data', index//6, want_data, actual)
            if select < 0xa0:
                returned.append(actual)
            else:
                registers.append([select, actual])
    assert not damaged and len(returned) == 504
    report(event='cold', image=binascii.hexlify(returned).decode(), registers=registers, rows=len(PLAN)//6)
    io.write_ui_in_byte(0)
    for gpio in (18, 19, 20, 28, 30, 31):
        Pin(gpio, Pin.IN, None)
    run.value(0)


def execute(item, ids):
    name = item[0]
    case = schedule(scenario, item)
    events = case['events']
    words = array.array('I')
    finish = tick(case['finish'])
    for i, (t, value) in enumerate(events):
        nxt = tick(events[i+1][0]) if i+1 < len(events) else finish + 128
        duration = nxt - tick(t)
        assert duration >= 4
        words.append(((duration-4) << 3) | value)
    count = 4*((finish + 64 + 3)//4)
    assert count < 65536
    capture = bytearray(count)
    changes = bytearray(min(6000, count))
    run = Pin(32, Pin.OUT, value=0)
    ck, tx, rx = ids
    # Restart in reserved loader mode with idle CS and clear the previous HALT.
    clk = rp2.StateMachine(ck, core_clock, freq=-1, set_base=Pin(16))
    driver = rp2.StateMachine(tx, requester, freq=-1, out_base=Pin(25))
    observe = rp2.StateMachine(rx, sampler, freq=-1, in_base=Pin(25))
    Pin(16, Pin.OUT, value=0)
    for gpio, v in ((25,0),(26,0),(27,1)):
        Pin(gpio, Pin.OUT, value=v)
    pulse()
    pulse()
    # Reinitialize PIO pad ownership after the two manually parked clocks.
    clk.init(core_clock, freq=-1, set_base=Pin(16))
    driver.init(requester, freq=-1, out_base=Pin(25))
    dma_tx = rp2.DMA()
    dma_rx = rp2.DMA()
    try:
        dma_tx.config(read=words, write=driver, count=len(words),
                      ctrl=dma_tx.pack_ctrl(size=2, inc_read=True, inc_write=False, treq_sel=tx), trigger=True)
        dma_rx.config(read=observe, write=capture, count=count//4,
                      ctrl=dma_rx.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4+rx), trigger=True)
        oe = machine.mem32[0xd0000030]
        assert not (oe & ((7 << 18) | (1 << 28) | (1 << 30) | (1 << 31)))
        driver.active(1)
        observe.active(1)
        run.value(1)
        time.sleep_us(3)
        clk.active(1)
        start = time.ticks_us()
        while dma_rx.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError('capture did not fill', name)
        status = io.read_uo_out_byte()
        assert not dma_tx.active()
    finally:
        clk.active(0)
        Pin(16, Pin.OUT, value=0)
        run.value(0)
        driver.active(0)
        observe.active(0)
        for dma in (dma_tx, dma_rx):
            dma.active(0)
            dma.close()
    size = pack_trace(capture, changes, count, len(changes))
    template = sum(((capture[i] >> 6) & 1) << i for i in range(10))
    data = changes[:size] if size > 0 else bytes(v & 127 for v in capture)
    report(event='trace', name=name, count=count, template=template, packed=size>0,
           data=binascii.hexlify(data).decode(), status=status)


def run_experiment():
    global tt
    tt = DemoBoard.get()
    hz, mode = machine.freq(), tt.mode
    free = [i for i in range(4) if not rp2.StateMachine(i).active()]
    assert len(free) >= 3
    report(event='start', original_hz=hz, suite=SUITE, mode=tt.mode_str, machines=free[:3])
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000
        load_program(True)
        load_program(False)
        for item in trials(SUITE):
            gc.collect()
            execute(item, free[:3])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for i in range(25, 33):
            Pin(i, Pin.IN, None)
        for program in (core_clock, requester, sampler):
            rp2.PIO(0).remove_program(program)
        machine.freq(hz)
        tt.mode = mode
    report(event='finish', restored_hz=machine.freq(), host_uio_oe=io.read_uio_outputenable())
