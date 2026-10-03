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

    def edge(self, program, *, rst_n=True, ena=True, sampled_inputs=0):
        if len(program) > MAX_PROGRAM_WORDS:
            raise ValueError("provisional M1 program exceeds 16 words")
        if not rst_n:
            self.pc = self.wait_left = self.gpio_value = self.gpio_oe = 0
            self.state = State.RUN
            self.wait_is_input = False
            self.wait_pin = self.wait_level = 0
            return
        if not ena or self.state in (State.HALT, State.FAULT):
            return
        if self.state is State.WAIT:
            if self.wait_is_input and ((sampled_inputs >> self.wait_pin) & 1) == self.wait_level:
                self.wait_left = 0
                self.pc += 1
                self.state = State.RUN
                self.wait_is_input = False
                return
            if self.wait_is_input and self.wait_left == 1:
                self.wait_left = 0
                self.state = State.FAULT
                return
            if self.wait_left > 1:
                self.wait_left -= 1
            else:
                self.wait_left = 0
                self.pc += 1
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
            self.pc += 1
        elif instruction.opcode == "WAIT":
            if instruction.count == 0:
                self.pc += 1
            else:
                self.wait_left = instruction.count
                self.state = State.WAIT
        elif instruction.opcode == "WAIT_PIN":
            selected = (sampled_inputs >> instruction.pin) & 1
            if selected == instruction.level:
                self.pc += 1
            elif instruction.count == 0:
                self.state = State.FAULT
            else:
                self.state = State.WAIT
                self.wait_left = instruction.count
                self.wait_is_input = True
                self.wait_pin = instruction.pin
                self.wait_level = instruction.level
        else:
            self.state = State.HALT
            self.wait_left = 0

    @staticmethod
    def _valid(instruction):
        if not isinstance(instruction, Instruction):
            return False
        if instruction.opcode == "SET":
            return all(0 <= field <= 0xFF for field in (instruction.mask, instruction.value, instruction.oe))
        if instruction.opcode == "WAIT":
            return 0 <= instruction.count <= MAX_WAIT
        if instruction.opcode == "WAIT_PIN":
            return 0 <= instruction.pin <= 7 and instruction.level in (0, 1) and 0 <= instruction.count <= MAX_WAIT
        return instruction.opcode == "HALT" and not any(
            (instruction.mask, instruction.value, instruction.oe, instruction.count,
             instruction.pin, instruction.level)
        )
