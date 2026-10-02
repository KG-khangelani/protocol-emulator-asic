"""Executable model of the proposed M1 contract; this is not production VM RTL."""

from dataclasses import dataclass
from enum import Enum, auto


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


@dataclass
class Machine:
    pc: int = 0
    state: State = State.RUN
    wait_left: int = 0
    gpio_value: int = 0
    gpio_oe: int = 0

    def edge(self, program, *, rst_n=True, ena=True):
        if not rst_n:
            self.pc = self.wait_left = self.gpio_value = self.gpio_oe = 0
            self.state = State.RUN
            return
        if not ena or self.state in (State.HALT, State.FAULT):
            return
        if self.state is State.WAIT:
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
            return instruction.count >= 0
        return instruction.opcode == "HALT" and not any(
            (instruction.mask, instruction.value, instruction.oe, instruction.count)
        )

