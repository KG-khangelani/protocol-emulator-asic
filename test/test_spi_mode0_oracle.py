# SPDX-License-Identifier: Apache-2.0
"""SPI schedule falsification and isolated reference tradeoffs, not ASIC proof."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m1_contract_model import Instruction, Machine, State
from tools.spi_mode0_oracle import (assemble, bits, coupled_program, coupled_result,
                                   expected_gpio, miso_level, schedule)
from tools.spi_phase_reference import PhaseReference, split_program


def run_reference(tx, rx, *, response=1, order=1, half_period=25, late=True, split=False):
    machine = PhaseReference() if split else Machine()
    program = split_program(half_period, msb_first=order) if split else coupled_program(
        half_period, msb_first=order, late=late)
    timing = schedule(half_period, late=late)
    captures, observed_tx, observed_rx = [], [], []
    for edge in range(1, timing["halt"] + 1):
        raw = miso_level(4 * (edge - 2), rx, half_period=half_period,
                         response_quarters=response, msb_first=order)
        machine.edge(program, sampled_inputs=raw << 1, tx_payload=tx)
        expected = expected_gpio(edge, tx, half_period=half_period,
                                 msb_first=order, late=False if split else late)
        if (machine.gpio_value, machine.gpio_oe) != expected:
            raise AssertionError((edge, machine.gpio_value, machine.gpio_oe, expected))
        if edge in timing["rising"]:
            observed_tx.append(machine.gpio_value & 1)
            observed_rx.append(miso_level(4 * edge, rx, half_period=half_period,
                                          response_quarters=response, msb_first=order))
        if machine.shift_result_write:
            captures.append((edge, machine.shift_result_data))
        if machine.state in (State.HALT, State.FAULT) and edge != timing["halt"]:
            raise AssertionError(("premature terminal", edge, machine.state))
    if (machine.state, machine.pc) != (State.HALT, 9 if split else 7):
        raise AssertionError((machine.state, machine.pc))
    if (assemble(observed_tx, order), assemble(observed_rx, order)) != (tx, rx):
        raise AssertionError("external rising-edge oracle disagrees")
    return machine, captures


class SpiMode0OracleTests(unittest.TestCase):
    def test_exact_table_and_input_validation(self):
        timing = schedule()
        self.assertEqual(timing["rising"], list(range(27, 378, 50)))
        self.assertEqual(timing["falling"], list(range(52, 403, 50)))
        self.assertEqual((timing["raw_capture"], timing["release"], timing["halt"]),
                         (376, 402, 403))
        self.assertEqual(bits(0x96), [1, 0, 0, 1, 0, 1, 1, 0])
        self.assertEqual(bits(0x96, 0), [0, 1, 1, 0, 1, 0, 0, 1])
        self.assertEqual(miso_level(4 * timing["release"], 0), 0)
        self.assertEqual(miso_level(4 * timing["release"] + 1, 0), 1)
        for bad in (0, 3, 65536, 4.5, True):
            with self.assertRaises(ValueError):
                coupled_program(bad)
        for response in (0, 97):
            with self.assertRaises(ValueError):
                miso_level(100, 0x69, response_quarters=response)
        with self.assertRaises(ValueError):
            PhaseReference().edge([Instruction("HALT")] * 17)

    def test_eight_words_all_bytes_conditionally_receive_fast_response(self):
        self.assertEqual(len(coupled_program()), 8)
        for order in (0, 1):
            for rx in range(256):
                machine, captures = run_reference(255 - rx, rx, order=order)
                self.assertEqual(captures, [(376, rx)])
                self.assertEqual(machine.shift_result_data, rx)

    def test_deadline_crossing_is_a_retained_counterexample_not_mode0_pass(self):
        for response, desired in ((88, 0x69), (89, 0xB4), (96, 0xB4)):
            machine, captures = run_reference(0x96, 0x69, response=response)
            self.assertEqual(captures, [(376, desired)])
            self.assertEqual(machine.shift_result_data, coupled_result(
                0x69, response_quarters=response))
        wrong = {order: 0 for order in (0, 1)}
        for order in wrong:
            for rx in range(256):
                machine, _ = run_reference(255 - rx, rx, order=order, response=89)
                wrong[order] += machine.shift_result_data != rx
        self.assertEqual(wrong, {0: 255, 1: 255})

    def test_early_control_fails_even_with_fast_target(self):
        machine, captures = run_reference(0x96, 0x69, late=False)
        self.assertEqual(captures, [(353, 0xB4)])
        self.assertNotEqual(machine.shift_result_data, 0x69)

    def test_split_reference_measures_ten_words_and_preserves_clock_bound(self):
        self.assertEqual((len(split_program()), 32 * len(split_program())), (10, 320))
        self.assertGreater(len(split_program()), 8, "not publicly loadable on this chip")
        for order in (0, 1):
            for rx in range(256):
                machine, captures = run_reference(255 - rx, rx, order=order,
                                                  response=96, split=True)
                self.assertEqual(captures, [(379, rx)])
                self.assertFalse(machine.prepared)
        for half in (4, 5):
            machine, captures = run_reference(0xA5, 0x69, half_period=half,
                                              response=4 * half - 4, split=True)
            self.assertEqual(captures, [(2 + 15 * half + 2, 0x69)])
            self.assertEqual(machine.state, State.HALT)

    def test_split_order_reset_disable_and_partial_halt(self):
        drive = Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1)
        sample = Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1)
        for program in ([object()], [sample], [drive, drive], [drive, Instruction("HALT")],
                        [drive, Instruction("SAMPLE", tx_pin=2, rx_pin=1, msb_first=1)]):
            machine = PhaseReference()
            for _ in program:
                machine.edge(program, tx_payload=0x96)
            self.assertEqual(machine.state, State.FAULT)
        machine = PhaseReference()
        machine.edge([drive, sample], tx_payload=0x96)
        before = vars(machine).copy()
        machine.edge([drive, sample], ena=False)
        self.assertEqual(vars(machine), before)
        machine.edge([drive, sample], rst_n=False, ena=False)
        self.assertFalse(machine.prepared)
        self.assertEqual((machine.pc, machine.gpio_oe, machine.shift_active), (0, 0, False))


if __name__ == "__main__":
    if sys.argv[1:] == ["--require-mode0"]:
        import json
        machine, captures = run_reference(0x96, 0x69, response=89)
        print(json.dumps({"hypothesis": "eight-word late schedule covers the full response envelope",
                          "result": "PASS" if machine.shift_result_data == 0x69 else "FAIL",
                          "tx": 0x96, "target_rx": 0x69,
                          "actual_rx": machine.shift_result_data,
                          "response_quarters": 89, "raw_captures": captures,
                          "terminal": machine.state.name, "pc": machine.pc}))
        raise SystemExit(int(machine.shift_result_data != 0x69))
    if sys.argv[1:] == ["--reference-cost"]:
        import json
        from dataclasses import fields
        coupled, first = run_reference(0x96, 0x69, response=89)
        split, second = run_reference(0x96, 0x69, response=96, split=True)
        extra = sorted({f.name for f in fields(PhaseReference)} -
                       {f.name for f in fields(Machine)})
        print(json.dumps({"rung": "REFERENCE_ONLY", "coupled_words": len(coupled_program()),
                          "split_words": len(split_program()), "word_bits": 32,
                          "trace_verified_accepted_edges_each": schedule()["halt"],
                          "coupled_capture": first, "split_capture": second,
                          "extra_reference_fields": extra, "real_store_words": 8,
                          "real_loader_byte_address_bits": 5,
                          "split_required_byte_address_bits": 6,
                          "additional_program_bits_if_expanded": 64,
                          "gate_area_timing_cost": "NOT_EVALUATED"}))
    else:
        unittest.main()
