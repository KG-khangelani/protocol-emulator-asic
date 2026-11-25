# SPDX-License-Identifier: Apache-2.0
"""Run directly with mpremote on a stock Pico. GP18 samples DQ at the sensor and GP19 is the master."""
import binascii
import json
import machine
import onewire
import os
import rp2
import time
from machine import Pin

SAMPLE_HZ = 2000000
SAMPLES = 16384


@rp2.asm_pio(in_shiftdir=rp2.PIO.SHIFT_RIGHT, autopush=True, push_thresh=32)
def sample_dq():
    in_(pins, 1)


def address(bus, rom, command):
    bus.reset(True)
    bus.writebyte(0x55)
    bus.write(rom)
    bus.writebyte(command)


def identification(bus):
    found = bus.scan()
    if len(found) != 1:
        raise ValueError("expected exactly one sensor", len(found))
    rom = found[0]
    if len(rom) != 8 or rom[0] != 0x28 or bus.crc8(rom):
        raise ValueError("invalid family or ROM CRC", binascii.hexlify(rom))
    scratch = bytearray(9)
    address(bus, rom, 0xbe)
    bus.readinto(scratch)
    if len(set(scratch)) == 1 or bus.crc8(scratch):
        raise ValueError("invalid scratchpad or CRC", binascii.hexlify(scratch))
    address(bus, rom, 0xb4)
    return dict(rom=binascii.hexlify(rom).decode(), scratchpad=binascii.hexlify(scratch).decode(),
                power=bus.readbit())


def broadcast(bus, tap, sm_id):
    buf = bytearray(SAMPLES // 8)
    receiver = rp2.StateMachine(sm_id, sample_dq, freq=SAMPLE_HZ, in_base=tap)
    channel = rp2.DMA()
    try:
        dreq = 8 * (sm_id // 4) + 4 + sm_id % 4
        channel.config(read=receiver, write=buf, count=len(buf)//4,
                       ctrl=channel.pack_ctrl(size=2, inc_read=False, inc_write=True, treq_sel=dreq), trigger=True)
        receiver.active(1)
        time.sleep_us(80)
        bus.reset(True)
        bus.writebyte(0xcc)
        bus.writebyte(0xb4)
        bit = bus.readbit()
        start = time.ticks_us()
        while channel.active():
            if time.ticks_diff(time.ticks_us(), start) > 30000:
                raise RuntimeError("DQ capture timed out")
    finally:
        receiver.active(0)
        channel.active(0)
        channel.close()
        rp2.PIO(sm_id // 4).remove_program(sample_dq)
    return bit, binascii.hexlify(buf).decode()


def observe(master, tap, sm_id, pull):
    if rp2.StateMachine(sm_id).active():
        raise RuntimeError("sampler is in use")
    if not master.value() or not tap.value():
        raise ValueError("DQ must be idle high at both inputs")
    bus = onewire.OneWire(master)
    try:
        # The library enables its own pull-up. The local sensor uses the measured external pull-up.
        master.init(Pin.OPEN_DRAIN, pull, value=1)
        before = identification(bus)
        bit, data = broadcast(bus, tap, sm_id)
        record = dict(before=before, power=bit, samples=SAMPLES, sample_hz=SAMPLE_HZ, dq_lsb_first=data)
        try:
            after = identification(bus)
            record["after"] = after
            if before["rom"] != after["rom"] or before["power"] != after["power"] or bit != before["power"]:
                raise ValueError("identity or power result changed")
        except Exception:
            # The waveform was acquired even if the device went away or its response changed later.
            print("SENSORREF_PARTIAL " + json.dumps(record))
            raise
        return record
    finally:
        master.init(Pin.IN, None)


def main():
    host = os.uname().machine
    if host != "Raspberry Pi Pico with RP2040":
        raise RuntimeError("this pin assignment requires the original Raspberry Pi Pico", host)
    master, tap = Pin(19, Pin.IN, None), Pin(18, Pin.IN, None)
    try:
        result = observe(master, tap, 4, None)
        result.update(fixture="local-pico", host=host, system_hz=machine.freq(), master_gpio=19, sensor_gpio=18)
        print("SENSORREF " + json.dumps(result))
    except Exception as exc:
        print("SENSORREF_ERROR " + json.dumps({"error": repr(exc)}))
        raise
    finally:
        master.init(Pin.IN, None)
        tap.init(Pin.IN, None)


if __name__ == "__main__":
    main()
