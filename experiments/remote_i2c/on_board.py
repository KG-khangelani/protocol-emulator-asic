# SPDX-License-Identifier: Apache-2.0
"""MicroPython payload for the native RP2350B I2C1 target and its independent pin capture."""
import binascii
import gc
import json
import machine
import rp2
import time
from machine import Pin
from ttboard.demoboard import DemoBoard
from ttboard.mode import RPMode
from ttboard.util.platform import rp2350 as io


def emit(**values):
    print("I2CLAB " + json.dumps(values))


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def project_clock():
    set(pins, 1) [4]
    set(pins, 0) [4]


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def samples():
    in_(pins, 8)


def pulse():
    io.write_clock(1)
    time.sleep_us(3)
    io.write_clock(0)
    time.sleep_us(3)


def load_program(tt, plan, name):
    Pin(32, Pin.OUT, value=0)
    io.write_uio_outputenable(0x80)
    Pin(32, Pin.OUT, value=0)
    stage = Pin(30, Pin.OUT, value=0)
    Pin(16, Pin.OUT, value=0)
    for gpio in range(17, 25):
        Pin(gpio, Pin.OUT, value=0)
    image = bytearray()
    registers = []
    last_reset = -1
    for offset in range(0, len(plan), 6):
        reset, selector, data, flags, status, expected = plan[offset:offset + 6]
        if reset != last_reset:
            tt.reset_project(not reset)
            last_reset = reset
        if flags & 1:
            stage.value(1)
            io.write_ui_in_byte(data)
            time.sleep_us(3)
            pulse()
            stage.value(0)
        io.write_ui_in_byte(0xe7 if flags & 8 else selector)
        time.sleep_us(3)
        pulse()
        actual = io.read_uo_out_byte()
        if flags & 2 and actual != status or flags & 4 and actual != expected:
            raise ValueError("cold readback", name, offset // 6, selector, actual, status, expected)
        if flags & 4:
            if selector < 0xa0:
                image.append(actual)
            else:
                registers.append([selector, actual])
    emit(event="cold", name=name, rows=len(plan) // 6, image=binascii.hexlify(image).decode(), registers=registers)
    io.write_ui_in_byte(0)
    # Free the low dedicated inputs, including both HAT paths to the I2C bus.
    for gpio in range(17, 21):
        Pin(gpio, Pin.IN, None)
    for gpio in range(25, 32):
        Pin(gpio, Pin.IN, None)
    Pin(30, Pin.IN, Pin.PULL_DOWN)


def transact(tt, name, plan, register, reply, target_address, machines):
    load_program(tt, plan, name)
    run = Pin(32, Pin.OUT, value=0)
    page = Pin(25, Pin.OUT, value=0)
    valid = Pin(28, Pin.OUT, value=0)
    sda = Pin(26, Pin.IN, Pin.PULL_UP)
    scl = Pin(27, Pin.IN, Pin.PULL_UP)
    if EXTRA_PULL:
        Pin(18, Pin.IN, Pin.PULL_UP)
        Pin(19, Pin.IN, Pin.PULL_UP)
    bank = bytearray(256)
    bank[register] = reply
    target = machine.I2CTarget(1, addr=target_address, mem=bank, mem_addrsize=8, scl=scl, sda=sda)
    clock_id, capture_id = machines
    capture = bytearray(24000)
    dma = rp2.DMA()
    clock = rp2.StateMachine(clock_id, project_clock, freq=-1, set_base=Pin(16))
    reader = rp2.StateMachine(capture_id, samples, freq=10000000, in_base=Pin(25))
    try:
        Pin(16, Pin.OUT, value=0)
        time.sleep_us(15)
        idle = [sda.value(), scl.value()]
        if idle != [1, 1]:
            raise ValueError("bus did not reach idle", name, idle)
        pulse()
        pulse()
        clock.init(project_clock, freq=-1, set_base=Pin(16))
        dma.config(read=reader, write=capture, count=len(capture) // 4,
                   ctrl=dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=4 + capture_id),
                   trigger=True)
        run.value(1)
        time.sleep_us(5)
        reader.active(1)
        clock.active(1)
        start = time.ticks_us()
        while dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("DMA capture timed out", name)
        status = io.read_uo_out_byte()
        clock.active(0)
        Pin(16, Pin.OUT, value=0)
        page.value(1)
        time.sleep_us(5)
        received = io.read_uo_out_byte()
        valid.value(1)
        time.sleep_us(5)
        received_valid = io.read_uo_out_byte()
    finally:
        clock.active(0)
        reader.active(0)
        dma.active(0)
        dma.close()
        Pin(16, Pin.OUT, value=0)
        run.value(0)
        target.deinit()
        for gpio in (18, 19):
            Pin(gpio, Pin.IN, None)
        for gpio in range(25, 32):
            Pin(gpio, Pin.IN, None)
    # GPIO26 SDA, 27 SCL, 29 controller SDA pull-low, 30 HALT. Discard unrelated pins.
    changes = []
    last = -1
    for index, raw in enumerate(capture):
        value = raw & 0x36
        if value != last:
            changes.append([index, value])
            last = value
            if len(changes) == 24:
                emit(event="pins", name=name, changes=changes)
                changes = []
    if changes:
        emit(event="pins", name=name, changes=changes)
    emit(event="trace", name=name, samples=len(capture), period_ns=100,
         target_address=target_address, register=register, reply=reply, idle=idle,
         status=status, rx=received, valid=received_valid)


def run():
    tt = DemoBoard.get()
    original_hz, mode = machine.freq(), tt.mode
    free = [i for i in range(4) if not rp2.StateMachine(i).active()]
    if len(free) < 2:
        raise RuntimeError("two PIO0 machines required")
    try:
        tt.clock_project_stop()
        tt.mode = RPMode.ASIC_RP_CONTROL
        machine.freq(125000000)
        assert machine.freq() == 125000000
        emit(event="start", system_hz=machine.freq(), project_divisor=10, capture_hz=10000000, linked_pulls=EXTRA_PULL,
             original_hz=original_hz, machines=free[:2])
        for clocks, register, reply, peer, key in TRIALS:
            gc.collect()
            name = "%d-%02x-%02x" % (clocks, register, peer)
            transact(tt, name, binascii.a2b_base64(PLANS[key]), register, reply, peer, free[:2])
    finally:
        Pin(32, Pin.OUT, value=0)
        Pin(16, Pin.OUT, value=0)
        tt.reset_project(True)
        for gpio in range(25, 33):
            Pin(gpio, Pin.IN, None)
        for program in (project_clock, samples):
            rp2.PIO(0).remove_program(program)
        machine.freq(original_hz)
        tt.mode = mode
    emit(event="finish", restored_hz=machine.freq(), host_uio_oe=io.read_uio_outputenable())


try:
    run()
finally:
    PLANS.clear()
    gc.collect()
