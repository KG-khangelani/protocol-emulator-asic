# SPDX-License-Identifier: Apache-2.0
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.spi_phase.phase_programs import PhaseMachine, compact_program, encode, plain_program
from tools.m1_contract_model import Instruction, State
from tools.spi_mode0_oracle import bits, expected_gpio, miso_level, schedule


class PhaseComparisonReferenceTests(unittest.TestCase):
    def test_actual_words_and_capacity(self):
        self.assertEqual([encode(w) for w in compact_program()],
                         [0x65000008, 0xB0486000, 0x40000017, 0x00040404,
                          0xB0500008, 0x40000015, 0x000C0C08, 0x80000000])
        self.assertEqual(len(plain_program()), 10)
        with self.assertRaises(ValueError):
            PhaseMachine().edge(plain_program())
        with self.assertRaises(ValueError):
            encode(compact_program()[1], compact=False)

    def test_both_variants_all_bytes_and_orders_at_latest_response(self):
        timing = schedule()
        for compact in (False, True):
            for order in (0, 1):
                for rx in range(256):
                    tx = 255 - rx
                    program = (compact_program if compact else plain_program)(msb_first=order)
                    machine = PhaseMachine(compact=compact)
                    captures = []
                    for edge in range(1, timing["halt"] + 1):
                        raw = miso_level(4 * (edge - 2), rx, response_quarters=96, msb_first=order)
                        machine.edge(program, sampled_inputs=raw << 1, tx_payload=tx)
                        value, oe = expected_gpio(edge, tx, late=False, msb_first=order)
                        if compact and edge >= 2:
                            index = min((edge - 2) // 50, 7)
                            value = (value & ~1) | bits(tx, order)[index]
                            oe |= 1
                        self.assertEqual((machine.gpio_value, machine.gpio_oe), (value, oe))
                        if machine.shift_result_write:
                            captures.append((edge, machine.shift_result_data))
                    self.assertEqual(captures, [(379, rx)])
                    self.assertEqual((machine.state, machine.pc), (State.HALT, 7 if compact else 9))

    def test_mixed_partial_modes_and_config_fault(self):
        drive = Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1)
        sample = Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1)
        old = Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1, msb_first=1)
        for program in ([sample], [drive, drive], [drive, old], [old, drive],
                        [drive, Instruction("HALT")],
                        [drive, Instruction("SAMPLE", tx_pin=2, rx_pin=1, msb_first=1)]):
            machine = PhaseMachine()
            for _ in program:
                machine.edge(program, tx_payload=0x96)
            self.assertEqual(machine.state, State.FAULT)
            self.assertFalse(machine.shift_result_write)

    def test_delayed_sample_latches_operands_and_freezes(self):
        drive = Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1)
        sample = Instruction("SAMPLE", count=3, tx_pin=0, rx_pin=1, msb_first=1)
        machine = PhaseMachine()
        for _ in range(7):
            machine.edge([drive], tx_payload=0x96)
            machine.pc = 0  # Direct instruction-port fixture, not a public program.
            machine.edge([Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1)])
            machine.pc = 0
        machine.edge([drive], tx_payload=0x96)
        machine.pc = 0
        machine.edge([sample])
        self.assertEqual((machine.state, machine.wait_left), (State.WAIT, 3))
        before = vars(machine).copy()
        machine.edge([Instruction("HALT")], ena=False, sampled_inputs=2)
        self.assertEqual(vars(machine), before)
        for _ in range(3):
            machine.edge([Instruction("HALT")], sampled_inputs=2)
        self.assertEqual((machine.shift_result_data, machine.shift_result_write), (1, True))
        self.assertFalse(machine.phase_active or machine.prepared)
        machine.edge([drive], rst_n=False, ena=False)
        self.assertEqual((machine.gpio_oe, machine.shift_active, machine.phase_active, machine.prepared),
                         (0, False, False, False))


if __name__ == "__main__":
    unittest.main()
