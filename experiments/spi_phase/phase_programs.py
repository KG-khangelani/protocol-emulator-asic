# SPDX-License-Identifier: Apache-2.0
"""Hand-authored experimental images and independent semantic extension.

No production compiler or VM imports this module. Capacity and new encodings
are explicit so an abstract ten-word list cannot masquerade as a real load.
"""

from dataclasses import dataclass

from tools.m1_contract_model import Instruction, Machine, State
from tools.spi_mode0_oracle import bits, check_half_period
from tools.spi_phase_reference import split_program


def compact_program(half_period=25, *, msb_first=1):
    check_half_period(half_period)
    bits(0, msb_first)
    return [Instruction("LOOP", length=5, count=8),
            Instruction("DRIVE", mask=12, value=0, tx_pin=0, rx_pin=1, msb_first=msb_first),
            Instruction("WAIT", count=half_period - 2),
            Instruction("SET", mask=4, value=4, oe=4),
            Instruction("SAMPLE", count=1, tx_pin=0, rx_pin=1, msb_first=msb_first),
            Instruction("WAIT", count=half_period - 4),
            Instruction("SET", mask=12, value=8, oe=12), Instruction("HALT")]


def plain_program(half_period=25, *, msb_first=1):
    return split_program(half_period, msb_first=msb_first)


def encode(word, *, compact=True):
    if word.opcode in ("DRIVE", "SAMPLE"):
        shape = Instruction("SHIFT_STEP", tx_pin=word.tx_pin, rx_pin=word.rx_pin,
                            msb_first=word.msb_first)
        if not Machine._valid(shape):
            raise ValueError("invalid phase pins/order")
        prefix = (2 << 30) | (1 << 29) | (word.msb_first << 28) | (word.tx_pin << 25) | (word.rx_pin << 22)
        if word.opcode == "DRIVE":
            if not 0 <= word.mask <= 255 or not 0 <= word.value <= 255 or word.mask & ((1 << word.tx_pin) | (1 << word.rx_pin)):
                raise ValueError("invalid auxiliary GPIO mask/value")
            if not compact and (word.mask or word.value):
                raise ValueError("plain DRIVE has no auxiliary update")
            return prefix | (1 << 19) | (word.mask << 11) | (word.value << 3)
        if not 0 <= word.count <= 65535 or (not compact and word.count):
            raise ValueError("invalid SAMPLE delay")
        return prefix | (2 << 19) | (word.count << 3)
    if word.opcode == "SET":
        return (word.mask << 16) | (word.oe << 8) | word.value
    if word.opcode == "WAIT":
        return (1 << 30) | word.count
    if word.opcode == "LOOP":
        return (1 << 30) | (1 << 29) | (word.length << 24) | word.count
    if word.opcode == "HALT":
        return 2 << 30
    if word.opcode == "SHIFT_STEP":
        return ((2 << 30) | (1 << 29) | (word.msb_first << 28) |
                (word.tx_pin << 25) | (word.rx_pin << 22) | (word.burst << 21) | (word.period << 5))
    raise ValueError("unsupported hand-authored image operation")


@dataclass
class PhaseMachine(Machine):
    phase_active: bool = False
    prepared: bool = False
    compact: bool = True

    @property
    def capacity(self):
        return 8 if self.compact else 10

    @property
    def shift_burst(self):
        return self.shift_period >= 2

    def capture(self, sampled_inputs):
        rx = (sampled_inputs >> self.shift_rx_pin) & 1
        self.shift_rx_data = (((self.shift_rx_data << 1) | rx) & 255 if self.shift_msb_first
                              else (rx << 7) | (self.shift_rx_data >> 1))
        self.prepared = False
        if self.shift_bits_done == 7:
            self.phase_active = self.shift_active = False
            self.shift_bits_done = 0
            self.shift_result_write = True
            self.shift_result_data = self.shift_rx_data
        else:
            self.shift_bits_done += 1
        self.wait_left = self.shift_period = 0
        self.state = State.RUN
        self._advance()

    def edge(self, program, *, rst_n=True, ena=True, sampled_inputs=0,
             tx_payload=0, tx_payload_alt=0):
        if len(program) > self.capacity:
            raise ValueError("image exceeds experimental public capacity")
        if not rst_n:
            self.phase_active = self.prepared = False
        self.shift_result_write = False
        if rst_n and ena and self.state is State.WAIT and self.shift_period == 1:
            if not self.phase_active or not self.prepared or not self.shift_active:
                self.state = State.FAULT
                self.wait_left = 0
            elif self.wait_left > 1:
                self.wait_left -= 1
            else:
                self.capture(sampled_inputs)
            return
        special = (rst_n and ena and self.state is State.RUN and self.pc < len(program)
                   and isinstance(program[self.pc], Instruction))
        word = program[self.pc] if special else None
        if special and word.opcode == "SHIFT_STEP" and self.phase_active:
            self.state = State.FAULT
            self.wait_left = 0
            return
        if not special or word.opcode not in ("DRIVE", "SAMPLE"):
            super().edge(program, rst_n=rst_n, ena=ena, sampled_inputs=sampled_inputs,
                         tx_payload=tx_payload, tx_payload_alt=tx_payload_alt)
            return
        try:
            encode(word, compact=self.compact)
        except ValueError:
            self.state = State.FAULT
            self.wait_left = 0
            return
        mismatch = self.shift_active and (word.tx_pin != self.shift_tx_pin or
                    word.rx_pin != self.shift_rx_pin or bool(word.msb_first) != self.shift_msb_first)
        if mismatch or (self.shift_active and not self.phase_active):
            self.state = State.FAULT
            self.wait_left = 0
            return
        if word.opcode == "DRIVE":
            if self.prepared:
                self.state = State.FAULT
                self.wait_left = 0
                return
            if not self.shift_active:
                self.shift_active = self.phase_active = True
                self.shift_bits_done = self.shift_rx_data = 0
                self.shift_tx_data = tx_payload
                self.shift_tx_pin, self.shift_rx_pin = word.tx_pin, word.rx_pin
                self.shift_msb_first = bool(word.msb_first)
            tx = (self.shift_tx_data >> (7 if self.shift_msb_first else 0)) & 1
            mask = 1 << self.shift_tx_pin
            self.gpio_value = ((self.gpio_value & ~word.mask & ~mask) |
                               (word.value & word.mask) | (tx << self.shift_tx_pin))
            self.gpio_oe = (self.gpio_oe | word.mask | mask) & ~(1 << self.shift_rx_pin)
            self.shift_tx_data = ((self.shift_tx_data << 1) & 255 if self.shift_msb_first
                                  else self.shift_tx_data >> 1)
            self.prepared = True
            self.shift_period = self.wait_left = 0
            self._advance()
        elif not self.phase_active or not self.prepared or not self.shift_active:
            self.state = State.FAULT
            self.wait_left = 0
        elif word.count:
            self.state = State.WAIT
            self.shift_period = 1
            self.wait_left = word.count
        else:
            self.capture(sampled_inputs)
