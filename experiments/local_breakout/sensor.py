# SPDX-License-Identifier: Apache-2.0
# prepare.py prepends the packed image, power mode and shared cold() function.
import binascii
import hashlib
import json
import machine
import onewire
import os
import rp2
import time
from machine import Pin


def emit(event, **fields):
    fields["event"] = event
    print("PICO1W " + json.dumps(fields))


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def project_clock():
    set(pins, 1) [4]
    set(pins, 0) [4]


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def sample_pins():
    in_(pins, 16)


class PicoPins:
    def __init__(self):
        self.run = Pin(16, Pin.OUT, value=0)
        self.reset = Pin(28, Pin.OUT, value=0)
        self.clock = Pin(27, Pin.OUT, value=0)
        self.stage = Pin(22, Pin.OUT, value=0)
        self.inputs = [Pin(i, Pin.IN, None) for i in range(8, 16)]
        self.outputs = [Pin(i, Pin.OUT, value=0) for i in range(8)]
        for i in (17, 18, 19, 20, 21, 26):
            Pin(i, Pin.IN, None)

    def set(self, reset, stage, byte):
        self.reset.value(reset)
        self.stage.value(stage)
        for i, pin in enumerate(self.outputs):
            pin.value((byte >> i) & 1)
        time.sleep_us(3)

    def pulse(self):
        self.clock.value(1)
        time.sleep_us(3)
        self.clock.value(0)
        time.sleep_us(3)

    def status(self):
        return (machine.mem32[0xd0000004] >> 8) & 255  # Atomic SIO GPIO_IN on the RP2040.

    def check(self, want, row, selector):
        return self.status()


def identity(dq):
    if dq.value() != 1:
        raise ValueError("idle DQ low before identity check")
    try:
        bus = onewire.OneWire(dq)
        roms = bus.scan()
        if MODE in ("stuck", "absent"):
            if roms or bus.reset():
                raise ValueError("control needs an empty bus")
            return "", None
        if len(roms) != 1 or roms[0][0] != 0x28 or bus.crc8(roms[0]) != 0:
            raise ValueError("single family-28 ROM with valid CRC required", roms)
        rom = roms[0]
        bus.reset(True)
        bus.writebyte(0x55)
        bus.write(rom)
        bus.writebyte(0xb4)
        bit = bus.readbit()
        if bit != int(MODE == "external"):
            raise ValueError("addressed power query disagrees with fixture", bit)
        return binascii.hexlify(rom).decode(), bit
    finally:
        dq.init(Pin.IN, None)  # external 4.7 kOhm during all FPGA samples


def capture(io, buf):
    # The stock Pico has two PIO blocks. PIO1 RX0 DREQ is 12.
    clk = rp2.StateMachine(0, project_clock, freq=-1, set_base=Pin(27))
    rx = rp2.StateMachine(4, sample_pins, freq=5000000, in_base=Pin(8))
    dma = rp2.DMA()
    try:
        io.clock.init(Pin.OUT, value=0)
        io.stage.init(Pin.IN, Pin.PULL_DOWN)
        Pin(17, Pin.OUT, value=0)
        Pin(20, Pin.OUT, value=0)
        if MODE == "stuck":
            Pin(19, Pin.OPEN_DRAIN, None, value=0)
        time.sleep_us(10)
        io.pulse()
        io.pulse()
        clk.init(project_clock, freq=-1, set_base=Pin(27))
        dma.config(read=rx, write=buf, count=len(buf)//4,
                   ctrl=dma.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=12), trigger=True)
        io.run.value(1)
        time.sleep_us(5)
        rx.active(1)
        clk.active(1)
        start = time.ticks_us()
        while dma.active():
            if time.ticks_diff(time.ticks_us(), start) > 40000:
                raise ValueError("capture timeout")
        return io.status()
    finally:
        clk.active(0)
        rx.active(0)
        dma.active(0)
        dma.close()
        io.clock.init(Pin.OUT, value=0)
        io.run.value(0)
        Pin(19, Pin.IN, None)
        rp2.PIO(0).remove_program(project_clock)
        rp2.PIO(1).remove_program(sample_pins)


def run_sensor():
    host = os.uname().machine
    if host != "Raspberry Pi Pico with RP2040" or any(rp2.StateMachine(i).active() for i in (0,4)):
        raise RuntimeError("use the dedicated stock RP2040 Pico with idle SM0/4", host)
    buf = bytearray(30000)
    before_hz = machine.freq()
    try:
        machine.freq(125000000)
        if machine.freq() != 125000000:
            raise ValueError("125 MHz system clock required")
        io = PicoPins()
        dq = Pin(19, Pin.IN, None)
        rom, bit = identity(dq)
        emit("identity", host=host, mode=MODE, rom=rom, reference_bit=bit)
        data, regs = cold(io, binascii.a2b_base64(PLAN))
        if binascii.hexlify(hashlib.sha256(data).digest()).decode() != IMAGE_SHA:
            raise ValueError("image readback hash")
        emit("cold", bytes=binascii.hexlify(data).decode(), registers=regs)
        status = capture(io, buf)
        time.sleep_us(500)
        if identity(dq) != (rom, bit):
            raise ValueError("sensor identity or addressed response changed after FPGA query")
    finally:
        Pin(16, Pin.OUT, value=0)
        Pin(27, Pin.OUT, value=0)
        Pin(28, Pin.OUT, value=0)
        for gpio in list(range(16)) + [17, 18, 19, 20, 21, 22, 26]:
            Pin(gpio, Pin.IN, None)
        machine.freq(before_hz)
    last = -1
    chunk = []
    for pos in range(0, len(buf), 2):
        val = (buf[pos] | buf[pos+1] << 8) & 0x4802
        if val != last:
            chunk.append([pos//2, val])
            last = val
        if len(chunk) == 20:
            emit("pins", changes=chunk)
            chunk = []
    if chunk:
        emit("pins", changes=chunk)
    emit("finish", samples=len(buf)//2, system_hz=125000000, sample_hz=5000000, clock_divisor=10,
         status=status, confirmed_rom=rom, confirmed_bit=bit, cleanup=(machine.freq() == before_hz))


run_sensor()
