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

    def test_wait_maximum_is_bounded_and_larger_value_faults(self):
        maximum = Machine()
        maximum.edge([Instruction("WAIT", count=0xFFFF)])
        self.assertEqual((maximum.state, maximum.wait_left), (State.WAIT, 0xFFFF))
        invalid = Machine()
        invalid.edge([Instruction("WAIT", count=0x10000)])
        self.assertEqual((invalid.state, invalid.pc), (State.FAULT, 0))

    def test_wait_pin_event_wins_on_final_eligible_edge(self):
        program = [Instruction("WAIT_PIN", pin=2, level=1, count=2), Instruction("HALT")]
        machine = Machine()
        machine.edge(program, sampled_inputs=0)
        self.assertEqual((machine.state, machine.pc, machine.wait_left), (State.WAIT, 0, 2))
        machine.edge(program, sampled_inputs=0)
        self.assertEqual(machine.wait_left, 1)
        machine.edge(program, sampled_inputs=0x04)
        self.assertEqual((machine.state, machine.pc, machine.wait_left), (State.RUN, 1, 0))

    def test_wait_pin_timeout_and_disabled_edge(self):
        program = [Instruction("WAIT_PIN", pin=3, level=1, count=2)]
        machine = Machine()
        machine.edge(program, sampled_inputs=0)
        machine.edge(program, ena=False, sampled_inputs=0x08)
        self.assertEqual((machine.state, machine.wait_left), (State.WAIT, 2))
        machine.edge(program, sampled_inputs=0)
        machine.edge(program, sampled_inputs=0)
        self.assertEqual((machine.state, machine.pc, machine.wait_left), (State.FAULT, 0, 0))

    def test_wait_pin_zero_timeout_and_invalid_fields_fault(self):
        for instruction in (
            Instruction("WAIT_PIN", pin=0, level=1, count=0),
            Instruction("WAIT_PIN", pin=8, level=1, count=1),
            Instruction("WAIT_PIN", pin=0, level=2, count=1),
        ):
            machine = Machine()
            machine.edge([instruction], sampled_inputs=0)
            self.assertEqual((machine.state, machine.pc), (State.FAULT, 0))

    def test_wait_pin_timeout_skip_distinguishes_paths(self):
        program = [
            Instruction("WAIT_PIN", pin=2, level=1, count=2, timeout_skip=1),
            Instruction("SET", mask=1, value=1, oe=1),
            Instruction("HALT"),
        ]
        event = Machine()
        event.edge(program, sampled_inputs=0)
        event.edge(program, sampled_inputs=0)
        event.edge(program, sampled_inputs=4)
        event.edge(program, sampled_inputs=4)
        event.edge(program, sampled_inputs=4)
        self.assertEqual((event.state, event.pc, event.gpio_value), (State.HALT, 2, 1))

        timeout = Machine()
        timeout.edge(program, sampled_inputs=0)
        timeout.edge(program, sampled_inputs=0)
        timeout.edge(program, sampled_inputs=0)
        timeout.edge(program, sampled_inputs=0)
        self.assertEqual((timeout.state, timeout.pc, timeout.gpio_value), (State.HALT, 2, 0))

    def test_bounded_loop_counts_and_enable_freeze(self):
        for count in (0, 1, 2, 255):
            program = [
                Instruction("LOOP", length=2, count=count),
                Instruction("SET", mask=1, value=1, oe=1),
                Instruction("SET", mask=1, value=0, oe=1),
                Instruction("HALT"),
            ]
            machine = Machine()
            machine.edge(program)
            before = Machine(**machine.__dict__)
            machine.edge(program, ena=False)
            self.assertEqual(machine, before)
            highs = 0
            edges = 1
            while machine.state is not State.HALT:
                machine.edge(program)
                edges += 1
                highs += machine.gpio_value & 1
            self.assertEqual((machine.pc, machine.gpio_value, edges), (3, 0, 2 * count + 2))
            self.assertEqual(highs, count)

    def test_nested_loop_faults(self):
        machine = Machine()
        program = [Instruction("LOOP", length=1, count=1), Instruction("LOOP", length=1, count=1)]
        machine.edge(program)
        machine.edge(program)
        self.assertEqual(machine.state, State.FAULT)

    def test_loop_target_cannot_alias_through_pc_wrap(self):
        machine = Machine()
        machine.edge([Instruction("LOOP", length=31, count=0)])
        self.assertEqual((machine.state, machine.pc), (State.FAULT, 0))


if __name__ == "__main__":
    unittest.main()
