# SPDX-License-Identifier: Apache-2.0
"""Independent first-CS interval tests and reference/public-capacity separation."""
import copy
import unittest
from experiments.spi_phase.phase_programs import PhaseMachine
from experiments.spi_phase.phase1_capacity import best_reference, evaluate
from tools.spi_four_mode_oracle import timing, assess


def literal_first_edge_trace(mode=1):
    # Hand-written H25 schedule for A1, independent of instructions/executor.
    cpol = mode >> 1
    leading = [26+50*j for j in range(8)]
    trailing = [51+50*j for j in range(8)]
    trace = []
    for n in range(428):
        sck = cpol ^ int(any(a <= n < b for a, b in zip(leading, trailing)))
        active = [j for j, a in enumerate(leading) if n >= a]
        mosi = ((0x96 >> active[-1]) & 1) if active else 0
        row = {"edge": n, "out": ((int(n >= 426) << 3) | (sck << 2) | mosi) if n else 0,
               "oe": (13 if n >= 26 else 12) if n else 0,
               "miso": ((0x69 >> active[-1]) & 1) if active else 1,
               "rx": 0x69 if n >= 425 else 0, "rx_valid": int(n >= 425),
               "state": "HALT" if n == 427 else "RUN"}
        trace.append(row)
    return trace


class Phase1CapacityTests(unittest.TestCase):
    def test_first_interval_counts_without_shortening_setup_or_hold(self):
        schedule = timing(1, 1)
        self.assertEqual(schedule["sample"], [51,101,151,201,251,301,351,401])
        self.assertEqual((schedule["leading"][0], schedule["release"], schedule["halt"]),
                         (26,426,427))
        self.assertEqual(assess(literal_first_edge_trace(), schedule, 0x96, 0x69, 0,
                               [75+50*j for j in range(8)]), [])

    def test_initial_clock_and_cs_edge_mutants_still_fail(self):
        schedule = timing(1, 1)
        for n in (0, 1):
            trace = literal_first_edge_trace()
            trace[n]["out"] ^= 4
            trace[n]["oe"] |= 4
            kinds = {e["kind"] for e in assess(trace, schedule, 0x96, 0x69, 0,
                                              [75+50*j for j in range(8)])}
            self.assertIn("idle_before_cs" if n == 0 else "pins", kinds)

    def test_mode3_cannot_claim_the_low_pull_as_high_idle(self):
        errors = assess(literal_first_edge_trace(3), timing(3, 1), 0x96, 0x69, 0,
                        [75+50*j for j in range(8)])
        self.assertEqual(errors, [{"kind": "idle_before_cs", "edge": 0}])
        with self.assertRaises(ValueError):
            timing(1, 0)

    def test_reference_saving_does_not_expand_the_real_machine(self):
        for mode, size in ((1,9), (3,10)):
            for order in (0,1):
                program = best_reference(mode, order)
                self.assertEqual(len(program), size)
                with self.assertRaises(ValueError):
                    PhaseMachine().edge(program)
                accepted, _ = evaluate(program, mode, order)
                self.assertTrue(accepted["accepted"])
                rejected, _ = evaluate(program, mode, order, profile="edge_only")
                self.assertFalse(rejected["accepted"])
                self.assertEqual(rejected["error_kinds"], ["received_byte"])


if __name__ == "__main__":
    unittest.main()
