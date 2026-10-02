"""Specification-level checks only; no production VM or RTL is exercised."""

import unittest

from tools.m1_contract_model import Instruction, Machine, State


class ContractModelTest(unittest.TestCase):
    def test_wait_edge_counts_and_enable_freeze(self):
        program = [Instruction("WAIT", count=2), Instruction("SET", mask=1, value=1, oe=1)]
        machine = Machine()
        machine.edge(program)
        self.assertEqual((machine.state, machine.pc, machine.wait_left), (State.WAIT, 0, 2))
        machine.edge(program, ena=False)
        self.assertEqual((machine.state, machine.pc, machine.wait_left), (State.WAIT, 0, 2))
        machine.edge(program)
        self.assertEqual(machine.wait_left, 1)
        machine.edge(program)
        self.assertEqual((machine.state, machine.pc), (State.RUN, 1))
        machine.edge(program)
        self.assertEqual((machine.gpio_value, machine.gpio_oe, machine.pc), (1, 1, 2))

    def test_wait_zero_executes_following_instruction_next_edge(self):
        program = [Instruction("WAIT", count=0), Instruction("HALT")]
        machine = Machine()
        machine.edge(program)
        self.assertEqual((machine.state, machine.pc), (State.RUN, 1))
        machine.edge(program)
        self.assertEqual((machine.state, machine.pc), (State.HALT, 1))

    def test_set_mask_updates_value_and_direction_together(self):
        machine = Machine(gpio_value=0xA5, gpio_oe=0x3C)
        machine.edge([Instruction("SET", mask=0x0F, value=0x03, oe=0x05)])
        self.assertEqual(machine.gpio_value, 0xA3)
        self.assertEqual(machine.gpio_oe, 0x35)

    def test_halt_fault_and_reset_priority(self):
        halted = Machine(gpio_value=0x55, gpio_oe=0xAA)
        halted.edge([Instruction("HALT")])
        halted.edge([Instruction("SET", mask=0xFF, value=0xFF, oe=0xFF)])
        self.assertEqual((halted.state, halted.pc, halted.gpio_value, halted.gpio_oe), (State.HALT, 0, 0x55, 0xAA))
        halted.edge([], rst_n=False, ena=False)
        self.assertEqual(halted, Machine())

        faulted = Machine(gpio_value=0x12, gpio_oe=0x34)
        faulted.edge([])
        self.assertEqual((faulted.state, faulted.pc, faulted.gpio_value, faulted.gpio_oe), (State.FAULT, 0, 0x12, 0x34))
        faulted.edge([Instruction("SET", mask=0xFF, value=0xFF, oe=0xFF)])
        self.assertEqual(faulted.state, State.FAULT)

    def test_invalid_instruction_faults_without_gpio_change(self):
        machine = Machine(gpio_value=0xC3, gpio_oe=0x5A)
        machine.edge([Instruction("RESERVED")])
        self.assertEqual((machine.state, machine.pc, machine.gpio_value, machine.gpio_oe), (State.FAULT, 0, 0xC3, 0x5A))


if __name__ == "__main__":
    unittest.main()

