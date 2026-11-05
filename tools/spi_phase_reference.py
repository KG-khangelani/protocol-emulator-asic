# SPDX-License-Identifier: Apache-2.0
"""Unencoded, model-only DRIVE/SAMPLE experiment; not the production VM.

The ten-word plan does NOT fit the public eight-word store. This measures a
reference tradeoff before selecting an ISA, expanding memory or changing RTL.
"""

from dataclasses import dataclass

from .m1_contract_model import MAX_PROGRAM_WORDS, Instruction, Machine, State
from .spi_mode0_oracle import check_half_period


def split_program(half_period=25, *, msb_first=1):
    check_half_period(half_period)
    if msb_first not in (0, 1):
        raise ValueError("bit order must be binary")
    return [Instruction("LOOP", length=7, count=8),
            Instruction("SET", mask=12, value=0, oe=12),
            Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=msb_first),
            Instruction("WAIT", count=half_period - 3),
            Instruction("SET", mask=4, value=4, oe=4),
            Instruction("WAIT", count=0),
            Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=msb_first),
            Instruction("WAIT", count=half_period - 4),
            Instruction("SET", mask=12, value=8, oe=12),
            Instruction("HALT")]


@dataclass
class PhaseReference(Machine):
    prepared: bool = False

    def edge(self, program, *, rst_n=True, ena=True, sampled_inputs=0,
             tx_payload=0, tx_payload_alt=0):
        if len(program) > MAX_PROGRAM_WORDS:
            raise ValueError("reference program exceeds the model's 16-word bound")
        if not rst_n:
            self.prepared = False
        special = (rst_n and ena and self.state is State.RUN and
                   self.pc < len(program) and isinstance(program[self.pc], Instruction) and
                   program[self.pc].opcode in ("DRIVE", "SAMPLE"))
        if not special:
            super().edge(program, rst_n=rst_n, ena=ena, sampled_inputs=sampled_inputs,
                         tx_payload=tx_payload, tx_payload_alt=tx_payload_alt)
            return
        instruction = program[self.pc]
        self.shift_result_write = False
        shape = Instruction("SHIFT_STEP", tx_pin=instruction.tx_pin,
                            rx_pin=instruction.rx_pin, msb_first=instruction.msb_first)
        mismatch = self.shift_active and (
            instruction.tx_pin != self.shift_tx_pin or
            instruction.rx_pin != self.shift_rx_pin or
            bool(instruction.msb_first) != self.shift_msb_first)
        if not Machine._valid(shape) or mismatch:
            self.state = State.FAULT
            return
        if instruction.opcode == "DRIVE":
            if self.prepared:
                self.state = State.FAULT
                return
            if not self.shift_active:
                self.shift_active = True
                self.shift_bits_done = self.shift_rx_data = 0
                self.shift_tx_data = tx_payload
                self.shift_tx_pin, self.shift_rx_pin = instruction.tx_pin, instruction.rx_pin
                self.shift_msb_first = bool(instruction.msb_first)
            tx = (self.shift_tx_data >> (7 if self.shift_msb_first else 0)) & 1
            mask = 1 << self.shift_tx_pin
            self.gpio_value = (self.gpio_value & ~mask) | (tx << self.shift_tx_pin)
            self.gpio_oe = (self.gpio_oe | mask) & ~(1 << self.shift_rx_pin)
            self.shift_tx_data = ((self.shift_tx_data << 1) & 255 if self.shift_msb_first
                                  else self.shift_tx_data >> 1)
            self.prepared = True
        else:
            if not self.shift_active or not self.prepared:
                self.state = State.FAULT
                return
            rx = (sampled_inputs >> self.shift_rx_pin) & 1
            self.shift_rx_data = (((self.shift_rx_data << 1) | rx) & 255
                                  if self.shift_msb_first else
                                  (rx << 7) | (self.shift_rx_data >> 1))
            self.prepared = False
            if self.shift_bits_done == 7:
                self.shift_active = False
                self.shift_bits_done = 0
                self.shift_result_write = True
                self.shift_result_data = self.shift_rx_data
            else:
                self.shift_bits_done += 1
        self._advance()
