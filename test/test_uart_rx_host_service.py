"""Host policy and independent register-lifetime checks; no VM execution."""

import unittest

from tools.uart_rx_host_service import HostReader, visible_raw
from tools.uart_rx_oracle import expected_schedule


def run_host(reader, first, second, *, period=434, terminal=None):
    schedule = expected_schedule(period=period)
    halt = schedule["halt"]
    final = halt if terminal is None else terminal
    for n in range(1, final + reader.gap + reader.latency):
        requests = reader.requests(n)
        raw, valid = visible_raw(n, first, second, period=period)
        status = (0xA7 if terminal is None else 0xE6) if n >= final else 0x65
        reader.observe(n, requests, status, valid, raw if any(r != "poll" for r in requests) else None)
        if n < halt:
            assert reader.accepted is None
    return reader


class HostDeadlineTests(unittest.TestCase):
    def test_every_small_period_poll_phase_at_last_safe_bound(self):
        c1, c2 = expected_schedule(period=4)["raw_capture"]
        for gap in range(1, 40):
            latency = 40 - gap
            for phase in range(1, gap + 1):
                with self.subTest(gap=gap, latency=latency, phase=phase):
                    reader = run_host(HostReader(4, gap, latency, phase), 0x96, 0x69, period=4)
                    self.assertEqual(reader.accepted, (0x96, 0x69))
                    first_edge = reader.events[0][0]
                    self.assertTrue(c1 <= first_edge < c2)
                    self.assertLessEqual(reader.events[-1][0], expected_schedule(period=4)["halt"] + 39)
        for period in (434, 32766):
            # Closed-form worst residue, without a large Cartesian phase sweep.
            c1, c2 = expected_schedule(period=period)["raw_capture"]
            gap, latency = 10 * period - 2, 2
            positive = c1 + gap - 1
            self.assertEqual(positive + latency, c2 - 1)
            self.assertEqual(visible_raw(c2 - 1, 0x5A, 0xA5, period=period), (0x5A, 1))

    def test_tentative_byte_is_not_acceptance_and_interrupt_discards_it(self):
        schedule = expected_schedule(period=4)
        for bad in (0, 1):
            reader = run_host(HostReader(4, 1, 1), 0x96, 0x69,
                              period=4, terminal=schedule["checked_stop"][bad])
            self.assertIsNone(reader.accepted)
            self.assertIsNone(reader.first)
            self.assertEqual(reader.rejected, "not-ready/fault")
            self.assertEqual(reader.events[0], (schedule["raw_capture"][0] + 1, "tentative", 0x96))
        reader = HostReader(4, 1, 1)
        reader.first = 0x96
        reader.interrupt("disable/reset/loader")
        self.assertIsNone(reader.first)
        self.assertIsNone(reader.accepted)
        self.assertEqual(reader.requests(1), ())
        with self.assertRaises(ValueError):
            HostReader(434, 4339, 2)  # One edge beyond admission.
        delivered = run_host(HostReader(4, 1, 1), 0x96, 0x69, period=4)
        delivered.interrupt("permitted disable after acceptance")
        self.assertEqual(delivered.accepted, (0x96, 0x69))
        self.assertIsNone(delivered.rejected)

    def test_overwrite_is_many_to_one_and_flag_does_not_detect_it(self):
        c1, c2 = expected_schedule()["raw_capture"]
        self.assertNotEqual(visible_raw(c1, 0x5A, 0xA5), visible_raw(c1, 0x96, 0xA5))
        for n in (c2, c2 + 1, expected_schedule()["halt"]):
            self.assertEqual(visible_raw(n, 0x5A, 0xA5), visible_raw(n, 0x96, 0xA5))
            self.assertEqual(visible_raw(n, 0x5A, 0xA5), (0xA5, 1))


if __name__ == "__main__":
    unittest.main()
