# SPDX-License-Identifier: Apache-2.0
"""Proposed general-instruction I2C programs; no protocol-specific operation.

These are experimental hand-assembled images, not the G3 user assembler.
The literal control uses SET for each transmitted bit. The compact schedule
uses general open-drain serial output and the existing alternate payload.
"""
from dataclasses import dataclass, replace
from tools.m1_contract_model import Instruction
from experiments.spi_phase.phase_programs import encode as phase_encode
from experiments.i2c.baseline_programs import encode as legacy_encode


@dataclass(frozen=True)
class GeneralInstruction(Instruction):
    open_drain: bool = False
    alternate: bool = False
    jump: int | str | None = None


def encode(word):
    if word.jump is not None:
        if word.opcode != "WAIT_PIN" or type(word.jump) is not int or not 0 <= word.jump <= 255 or word.timeout_skip:
            raise ValueError("bounded branch needs an absolute byte target and no legacy skip")
        return legacy_encode(word) | (1 << 24) | (word.jump << 16)
    if word.open_drain or word.alternate:
        if word.opcode not in ("DRIVE", "SHIFT_STEP") or word.burst:
            raise ValueError("serial options apply only to manual SHIFT_STEP and DRIVE")
    if word.opcode in ("DRIVE", "SAMPLE", "SHIFT_STEP"):
        return phase_encode(word) | int(word.open_drain) | (int(word.alternate) << 1)
    return legacy_encode(word)


def image(kind, address, payload, *, variant="od128"):
    if kind not in ("write", "read", "write_read") or not 8 <= address <= 119 or not 0 <= payload <= 255:
        raise ValueError("ordinary address, byte and one of the three frozen transactions required")
    if variant not in ("od128", "literal255"):
        raise ValueError("unknown experiment")
    compact = variant == "od128"
    program, labels = [], {}

    def emit(opcode, **fields):
        program.append(GeneralInstruction(opcode, **fields))

    def set_bus(mask, oe):
        emit("SET", mask=mask, oe=oe)

    def wait(count):
        emit("WAIT", count=count)

    def await_clock():
        emit("WAIT_PIN", pin=0, level=1, count=49999, jump="timeout")

    def tx_bit(*, bit=None, alternate=False, force=None):
        if compact:
            emit("DRIVE", tx_pin=1, rx_pin=5, msb_first=1, mask=1,
                 open_drain=True, alternate=alternate)
            if force is not None:
                set_bus(2, 0 if force else 2)
        else:
            set_bus(2, 0 if bit else 2)
        wait(260)
        set_bus(1, 0)
        await_clock()
        if compact:
            emit("SAMPLE", tx_pin=1, rx_pin=5, msb_first=1, count=240)
        else:
            wait(240)
        set_bus(1, 1)

    def tx_byte(value, *, alternate=False, read_address=False):
        if compact:
            emit("LOOP", length=6, count=7 if read_address else 8)
            tx_bit(alternate=alternate)
            if read_address:
                # TX0 is the write address in a combined transfer. Override only
                # its final R/W bit using ordinary direction control during low.
                tx_bit(alternate=alternate, force=1)
        else:
            for bit in f"{value:08b}":
                tx_bit(bit=int(bit))

    def ack():
        set_bus(2, 0)
        wait(260)
        set_bus(1, 0)
        await_clock()
        wait(240)
        emit("WAIT_PIN", pin=1, level=0, count=0, jump="nack")
        set_bus(1, 1)

    def stop(marker):
        set_bus(2, 2)
        wait(260)
        set_bus(1, 0)
        await_clock()
        wait(200)
        set_bus(2, 0)
        wait(235)
        emit("SET", mask=31, oe=28, value=marker << 2)
        emit("HALT")

    emit("SET", mask=31, oe=28)
    wait(235)
    set_bus(2, 2)
    wait(200)
    set_bus(1, 1)
    tx_byte(address*2+int(kind == "read"))
    ack()
    if kind != "read":
        tx_byte(payload, alternate=True)
        ack()
    if kind == "write_read":
        set_bus(2, 0)
        wait(260)
        set_bus(1, 0)
        await_clock()
        wait(235)
        set_bus(2, 2)
        wait(200)
        set_bus(1, 1)
        tx_byte(address*2+1, read_address=True)
        ack()
    if kind != "write":
        emit("LOOP", length=6 if compact else 5, count=8)
        wait(260)
        set_bus(1, 0)
        await_clock()
        wait(240)
        emit("SHIFT_STEP", tx_pin=0, rx_pin=1, msb_first=1, open_drain=compact)
        if compact:
            # A one in TX0 releases SCL; this SET provides the falling edge.
            # A zero already lowered SCL on SHIFT_STEP. Both keep SDA stable.
            set_bus(1, 1)
        set_bus(2, 0)  # Controller NACKs its single received byte.
        wait(260)
        set_bus(1, 0)
        await_clock()
        wait(240)
        set_bus(1, 1)
    stop(1)
    labels["nack"] = len(program)
    set_bus(1, 1)
    stop(2)
    labels["timeout"] = len(program)
    emit("SET", mask=31, oe=28, value=12)
    emit("HALT")
    program = [replace(w, jump=labels[w.jump]) if isinstance(w.jump, str) else w for w in program]
    capacity = 128 if compact else 255
    if len(program) > capacity:
        raise ValueError(f"{len(program)} words exceed {variant} capacity {capacity}")
    # The literal control needs TX0=0 solely for the proven clock/capture reuse.
    data = {1: address*2+int(kind == "read") if compact else 0, 4: payload if compact else 0}
    return program, data, labels
