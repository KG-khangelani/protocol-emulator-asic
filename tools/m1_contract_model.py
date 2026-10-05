"""Executable model of the proposed M1 contract; this is not production VM RTL."""

from dataclasses import dataclass
from enum import Enum, auto

MAX_WAIT = 0xFFFF
MAX_PROGRAM_WORDS = 16


class State(Enum):
    RUN = auto()
    WAIT = auto()
    HALT = auto()
    FAULT = auto()


@dataclass(frozen=True)
class Instruction:
    opcode: str
    mask: int = 0
    value: int = 0
    oe: int = 0
    count: int = 0
    pin: int = 0
    level: int = 0
    timeout_skip: int = 0
    length: int = 0
    msb_first: int = 0
    tx_pin: int = 0
    rx_pin: int = 0
    burst: int = 0
    period: int = 0


@dataclass
class Machine:
    pc: int = 0
    state: State = State.RUN
    wait_left: int = 0
    gpio_value: int = 0
    gpio_oe: int = 0
    wait_is_input: bool = False
    wait_pin: int = 0
    wait_level: int = 0
    wait_timeout_skip: bool = False
    loop_active: bool = False
    loop_start: int = 0
    loop_end: int = 0
    loop_remaining: int = 0
    shift_active: bool = False
    shift_bits_done: int = 0
    shift_msb_first: bool = False
    shift_tx_pin: int = 0
    shift_rx_pin: int = 0
    shift_tx_data: int = 0
    shift_rx_data: int = 0
    shift_period: int = 0
    shift_tx_slot: int = 0
    shift_result_write: bool = False
    shift_result_data: int = 0

    @property
    def wait_is_shift(self):
        return self.shift_period != 0

    @property
    def shift_burst(self):
        return self.shift_period != 0

    def _advance(self):
        if self.loop_active and self.pc + 1 == self.loop_end:
            if self.loop_remaining > 1:
                self.pc = self.loop_start
                self.loop_remaining -= 1
            else:
                self.pc = self.loop_end
                self.loop_remaining = 0
                self.loop_active = False
        else:
            self.pc += 1

    def edge(self, program, *, rst_n=True, ena=True, sampled_inputs=0,
             tx_payload=0, tx_payload_alt=0):
        if len(program) > MAX_PROGRAM_WORDS:
            raise ValueError("provisional M1 program exceeds 16 words")
        if not rst_n:
            self.pc = self.wait_left = self.gpio_value = self.gpio_oe = 0
            self.state = State.RUN
            self.wait_is_input = False
            self.wait_pin = self.wait_level = 0
            self.wait_timeout_skip = False
            self.loop_active = False
            self.loop_start = self.loop_end = self.loop_remaining = 0
            self.shift_active = False
            self.shift_bits_done = 0
            self.shift_msb_first = False
            self.shift_tx_pin = self.shift_rx_pin = 0
            self.shift_tx_data = self.shift_rx_data = 0
            self.shift_period = 0
            self.shift_tx_slot = 0
            self.shift_result_write = False
            self.shift_result_data = 0
            return
        self.shift_result_write = False
        if not ena or self.state in (State.HALT, State.FAULT):
            return
        if self.state is State.WAIT:
            if self.wait_is_shift:
                if self.wait_left > 1:
                    self.wait_left -= 1
                    return
                if self.shift_active:
                    tx_bit = (self.shift_tx_data >>
                              (7 if self.shift_msb_first else 0)) & 1
                    rx_bit = (sampled_inputs >> self.shift_rx_pin) & 1
                    tx_mask = 1 << self.shift_tx_pin
                    rx_mask = 1 << self.shift_rx_pin
                    self.gpio_value = ((self.gpio_value & ~tx_mask) |
                                       (tx_bit << self.shift_tx_pin))
                    self.gpio_oe = (self.gpio_oe | tx_mask) & ~rx_mask
                    if self.shift_msb_first:
                        next_tx = (self.shift_tx_data << 1) & 0xFF
                        next_rx = ((self.shift_rx_data << 1) | rx_bit) & 0xFF
                    else:
                        next_tx = self.shift_tx_data >> 1
                        next_rx = ((rx_bit << 7) | (self.shift_rx_data >> 1)) & 0xFF
                    self.shift_tx_data = next_tx
                    self.shift_rx_data = next_rx
                    if self.shift_bits_done == 7:
                        self.shift_active = False
                        self.shift_bits_done = 0
                        self.shift_result_write = True
                        self.shift_result_data = next_rx
                        self.shift_tx_slot ^= 1
                        self.wait_left = self.shift_period - 1
                    else:
                        self.shift_bits_done += 1
                        self.wait_left = self.shift_period
                    return
                self.wait_left = 0
                self.shift_period = 0
                self._advance()
                self.state = State.RUN
                return
            if self.wait_is_input and ((sampled_inputs >> self.wait_pin) & 1) == self.wait_level:
                self.wait_left = 0
                self._advance()
                self.state = State.RUN
                self.wait_is_input = False
                return
            if self.wait_is_input and self.wait_left == 1:
                self.wait_left = 0
                self.wait_is_input = False
                if self.wait_timeout_skip:
                    if self.loop_active:
                        self.state = State.FAULT
                    else:
                        self.pc += 2
                        self.state = State.RUN
                else:
                    self.state = State.FAULT
                return
            if self.wait_left > 1:
                self.wait_left -= 1
            else:
                self.wait_left = 0
                self._advance()
                self.state = State.RUN
            return
        if self.pc >= len(program):
            self.state = State.FAULT
            self.wait_left = 0
            return
        instruction = program[self.pc]
        if not self._valid(instruction):
            self.state = State.FAULT
            self.wait_left = 0
        elif instruction.opcode == "SET":
            inverse_mask = (~instruction.mask) & 0xFF
            self.gpio_value = (self.gpio_value & inverse_mask) | (instruction.value & instruction.mask)
            self.gpio_oe = (self.gpio_oe & inverse_mask) | (instruction.oe & instruction.mask)
            self._advance()
        elif instruction.opcode == "WAIT":
            if instruction.count == 0:
                self._advance()
            else:
                self.wait_left = instruction.count
                self.state = State.WAIT
        elif instruction.opcode == "WAIT_PIN":
            selected = (sampled_inputs >> instruction.pin) & 1
            if selected == instruction.level:
                self._advance()
            elif instruction.count == 0:
                if instruction.timeout_skip:
                    if self.loop_active:
                        self.state = State.FAULT
                    else:
                        self.pc += 2
                else:
                    self.state = State.FAULT
            else:
                self.state = State.WAIT
                self.wait_left = instruction.count
                self.wait_is_input = True
                self.wait_pin = instruction.pin
                self.wait_level = instruction.level
                self.wait_timeout_skip = bool(instruction.timeout_skip)
        elif instruction.opcode == "LOOP":
            target = self.pc + instruction.length + 1
            if self.loop_active or target > 31:
                self.state = State.FAULT
            elif instruction.count == 0:
                self.pc = target
            else:
                self.loop_active = True
                self.loop_start = self.pc + 1
                self.loop_end = target
                self.loop_remaining = instruction.count
                self.pc += 1
        elif instruction.opcode == "SHIFT_STEP":
            if self.shift_active and (
                bool(instruction.msb_first) != self.shift_msb_first
                or instruction.tx_pin != self.shift_tx_pin
                or instruction.rx_pin != self.shift_rx_pin
                or instruction.burst
            ):
                self.state = State.FAULT
                self.wait_left = 0
                return
            order = self.shift_msb_first if self.shift_active else bool(instruction.msb_first)
            tx_pin = self.shift_tx_pin if self.shift_active else instruction.tx_pin
            rx_pin = self.shift_rx_pin if self.shift_active else instruction.rx_pin
            payload = tx_payload_alt if (instruction.burst and self.shift_tx_slot) else tx_payload
            tx_data = self.shift_tx_data if self.shift_active else payload
            rx_data = self.shift_rx_data if self.shift_active else 0
            tx_bit = (tx_data >> (7 if order else 0)) & 1
            rx_bit = (sampled_inputs >> rx_pin) & 1
            tx_mask = 1 << tx_pin
            rx_mask = 1 << rx_pin
            self.gpio_value = (self.gpio_value & ~tx_mask) | (tx_bit << tx_pin)
            self.gpio_oe = (self.gpio_oe | tx_mask) & ~rx_mask
            if order:
                next_tx = (tx_data << 1) & 0xFF
                next_rx = ((rx_data << 1) | rx_bit) & 0xFF
            else:
                next_tx = tx_data >> 1
                next_rx = ((rx_bit << 7) | (rx_data >> 1)) & 0xFF
            self.shift_tx_data = next_tx
            self.shift_rx_data = next_rx
            if not self.shift_active:
                self.shift_active = True
                self.shift_bits_done = 1
                self.shift_msb_first = order
                self.shift_tx_pin = tx_pin
                self.shift_rx_pin = rx_pin
                self.shift_period = instruction.period if instruction.burst else 0
            elif self.shift_bits_done == 7:
                self.shift_active = False
                self.shift_bits_done = 0
                self.shift_result_write = True
                self.shift_result_data = next_rx
            else:
                self.shift_bits_done += 1
            if instruction.burst:
                self.state = State.WAIT
                self.wait_left = instruction.period
            else:
                self._advance()
        else:
            self.state = State.FAULT if (self.loop_active or self.shift_active) else State.HALT
            self.wait_left = 0

    @staticmethod
    def _valid(instruction):
        if not isinstance(instruction, Instruction):
            return False
        if instruction.opcode == "SET":
            return all(0 <= field <= 0xFF for field in (instruction.mask, instruction.value, instruction.oe))
        if instruction.opcode == "WAIT":
            return 0 <= instruction.count <= MAX_WAIT
        if instruction.opcode == "LOOP":
            return 1 <= instruction.length <= 31 and 0 <= instruction.count <= 0xFF
        if instruction.opcode == "WAIT_PIN":
            return (0 <= instruction.pin <= 7 and instruction.level in (0, 1)
                    and instruction.timeout_skip in (0, 1)
                    and 0 <= instruction.count <= MAX_WAIT)
        if instruction.opcode == "SHIFT_STEP":
            return (instruction.msb_first in (0, 1)
                    and 0 <= instruction.tx_pin <= 7
                    and 0 <= instruction.rx_pin <= 7
                    and instruction.tx_pin != instruction.rx_pin
                    and instruction.burst in (0, 1)
                    and ((not instruction.burst and instruction.period == 0)
                         or (instruction.burst and 2 <= instruction.period <= MAX_WAIT)))
        return instruction.opcode == "HALT" and not any(
            (instruction.mask, instruction.value, instruction.oe, instruction.count,
             instruction.pin, instruction.level, instruction.timeout_skip,
             instruction.length, instruction.msb_first, instruction.tx_pin,
             instruction.rx_pin, instruction.burst, instruction.period)
        )
