# SPDX-License-Identifier: Apache-2.0
"""Existing-ISA I2C feasibility kernels, not a new assembler or instruction set."""
from tools.m1_contract_model import Instruction as I


def encode(word):
    if word.opcode == "SET":
        return word.mask << 16 | word.oe << 8 | word.value
    if word.opcode == "WAIT":
        return 1 << 30 | word.count
    if word.opcode == "WAIT_PIN":
        return 3 << 30 | word.pin << 27 | word.level << 26 | word.timeout_skip << 25 | word.count
    if word.opcode == "LOOP":
        return 1 << 30 | 1 << 29 | word.length << 24 | word.count
    if word.opcode == "HALT":
        return 2 << 30
    raise ValueError(word.opcode)


def wait_kernel(*, loop=False, skip=True):
    """Public release/event/timeout experiment, deliberately not an I2C frame.

    The ten-word version has an inline two-word cleanup path. LOOP count zero
    skips it after a successful wait. Timeout skip selects it. The seven-word
    loop version exposes the existing no-skip-inside-LOOP fault behavior.
    """
    first = [I("SET", mask=31, oe=28), I("SET", mask=3, oe=3)]
    wait = I("WAIT_PIN", pin=0, level=1, count=49999, timeout_skip=int(skip))
    if loop:
        return first + [I("LOOP", length=3, count=1), I("SET", mask=1),
                        wait, I("SET", mask=31, oe=28, value=4), I("HALT")]
    return first + [I("WAIT", count=258), I("SET", mask=1), wait,
                    I("LOOP", length=2, count=0),
                    I("SET", mask=31, oe=28, value=12), I("HALT"),
                    I("SET", mask=31, oe=28, value=4), I("HALT")]


def write_wire_baseline(address, payload):
    """Literal success-wire schedule with existing SET/WAIT/WAIT_PIN only.

    Capacity measurement, not an accepted full contract: no conditional ACK
    handling, no timeout cleanup, no receive. WAIT_PIN includes its real
    observation/dispatch overhead, so 100 kHz is a target, not an attained rate.
    No oversized program is aliased into the real loader.
    """
    if not 8 <= address <= 119 or not 0 <= payload <= 255:
        raise ValueError("ordinary address and byte required")
    words = [I("SET", mask=31, oe=28), I("WAIT", count=233),
             I("SET", mask=2, oe=2), I("WAIT", count=198), I("SET", mask=1, oe=1)]
    for byte in (address*2, payload):
        for bit in [int(c) for c in f"{byte:08b}"]+[1]:
            words += [I("SET", mask=2, oe=0 if bit else 2), I("WAIT", count=257),
                      I("SET", mask=1), I("WAIT_PIN", pin=0, level=1, count=49999),
                      I("WAIT", count=237), I("SET", mask=1, oe=1)]
    words += [I("SET", mask=2, oe=2), I("WAIT", count=257), I("SET", mask=1),
              I("WAIT_PIN", pin=0, level=1, count=49999), I("WAIT", count=198),
              I("SET", mask=2), I("WAIT", count=233), I("SET", mask=28, oe=28, value=4),
              I("HALT")]
    return words
