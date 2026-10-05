"""Focused semantic feasibility checks, not UART-RX RTL qualification."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from m1_contract_model import Machine, State
from uart_rx_oracle import Frame, expected_schedule, line_level, rx_program


class UartRxContractTests(unittest.TestCase):
    def run_reference(self, line, *, period=434, bound):
        machine = Machine()
        program = rx_program(period)
        captures, start_checks, stop_checks = [], [], []
        terminal_edge = None
        for edge in range(1, bound + 1):
            # Second-stage input consumed on this edge is raw input at edge-2.
            sampled = line(4 * (edge - 2)) << 1
            if machine.state is State.RUN and machine.pc == 3:
                start_checks.append(edge)
            if machine.state is State.RUN and machine.pc == 6:
                stop_checks.append(edge)
            machine.edge(program, sampled_inputs=sampled,
                         tx_payload=255, tx_payload_alt=255)
            if machine.gpio_oe & 2:
                self.fail(f"RX was driven on accepted edge {edge}")
            if machine.shift_result_write:
                captures.append((edge, machine.shift_result_data))
            if machine.state in (State.HALT, State.FAULT):
                terminal_edge = edge
                break
        return machine, terminal_edge, captures, start_checks, stop_checks

    def test_exact_frames_payloads_phase_and_capture_schedule(self):
        # Exhaust payloads once; phase corners use retained discriminating bytes.
        cases = [(434, 18, value, 255 - value) for value in range(256)]
        cases += [(434, 16 + phase, a, b)
                  for phase in (0, 1, 3) for a, b in ((0, 255), (85, 170))]
        cases.append((4, 17, 96, 69))  # Smallest legal firmware period.
        for period, start, first, second in cases:
            with self.subTest(period=period, phase=start % 4, bytes=(first, second)):
                frames = [Frame(first), Frame(second)]
                schedule = expected_schedule(start_quarter=start, period=period)
                line = lambda quarter: line_level(
                    quarter, frames, start_quarter=start, period=period)
                machine, terminal, captures, starts, stops = self.run_reference(
                    line, period=period, bound=schedule["halt"])
                self.assertEqual((machine.state, machine.pc, terminal),
                                 (State.HALT, 7, schedule["halt"]))
                self.assertEqual(captures, list(zip(schedule["raw_capture"],
                                                   (first, second))))
                self.assertEqual(starts, schedule["checked_start"])
                self.assertEqual(stops, schedule["checked_stop"])
                # A single final raw register is not lossless two-byte delivery.
                self.assertEqual(machine.shift_result_data, second)
                self.assertEqual((machine.gpio_value, machine.gpio_oe), (1, 1))

    def test_missing_start_and_high_at_start_center_fail_bounded(self):
        period, start = 434, 17
        machine, terminal, captures, _, _ = self.run_reference(
            lambda quarter: 1, period=period, bound=2 + 2 * period)
        self.assertEqual((machine.state, machine.pc, terminal, captures),
                         (State.FAULT, 1, 2 + 2 * period, []))
        # Pulse returns high before the sampled start center; not glitch filtering.
        short = lambda quarter: int(not start <= quarter < start + period)
        schedule = expected_schedule(start_quarter=start, period=period)
        machine, terminal, captures, _, _ = self.run_reference(
            short, period=period, bound=schedule["checked_start"][0])
        self.assertEqual((machine.state, machine.pc, terminal, captures),
                         (State.FAULT, 3, schedule["checked_start"][0], []))
        with self.assertRaises(ValueError):
            rx_program(32768)  # 2P would overflow the 16-bit timeout operand.

    def test_bad_stop_in_either_frame_is_not_validated_capture(self):
        schedule = expected_schedule()
        for bad_frame in (0, 1):
            frames = [Frame(96, int(bad_frame != 0)),
                      Frame(69, int(bad_frame != 1))]
            machine, terminal, captures, _, stops = self.run_reference(
                lambda quarter: line_level(quarter, frames),
                bound=schedule["checked_stop"][bad_frame])
            self.assertEqual((machine.state, machine.pc, terminal),
                             (State.FAULT, 6, schedule["checked_stop"][bad_frame]))
            self.assertEqual(captures, list(zip(
                schedule["raw_capture"][:bad_frame + 1],
                (96, 69)[:bad_frame + 1])))
            self.assertEqual(stops, schedule["checked_stop"][:bad_frame + 1])
            # Data capture happened earlier even for the malformed frame.
            self.assertEqual(machine.shift_result_data, (96, 69)[bad_frame])


if __name__ == "__main__":
    unittest.main()
