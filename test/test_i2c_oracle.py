# SPDX-License-Identifier: Apache-2.0
"""Hand calculations, finite reference sweeps and hostile I2C trace controls."""
import copy
from dataclasses import replace
import random
import unittest

from tools.i2c_oracle import Transaction, assess, assess_abort, observation_edge
from tools.i2c_reference import waveform

SEED = 0x12C2026


def kinds(rows, case):
    return {e["kind"] for e in assess(rows, case)["errors"]}


def resolve(rows):
    for row in rows:
        row["bus"] = 3 & ~(row["oe"] | row["target_oe"])
    return rows


def change_interval(rows, begin, end, **values):
    result = copy.deepcopy(rows)
    for row in result:
        if begin <= row["t"] < end:
            row.update(values)
    return resolve(result)


def insert(rows, tick, **values):
    result = copy.deepcopy(rows)
    prior = max((r for r in result if r["t"] <= tick), key=lambda r: r["t"])
    row = dict(prior, t=tick, **values)
    result = [r for r in result if r["t"] != tick] + [row]
    return resolve(sorted(result, key=lambda r: r["t"]))


class I2COracleTests(unittest.TestCase):
    def assert_pass(self, case, **fixture):
        rows = waveform(case, **fixture)
        report = assess(rows, case)
        self.assertEqual(report["errors"], [], (case, fixture, report["errors"][:8]))
        return rows, report

    def test_hand_calculated_write(self):
        case = Transaction(kind="write", tx=0x96)
        rows, report = self.assert_pass(case)
        bits = [e for e in report["events"] if e["kind"] == "BIT"]
        self.assertEqual([b["value"] for b in bits],
                         [1,0,1,0,0,1,0,0,0, 1,0,0,1,0,1,1,0,0])
        self.assertEqual([b["t"] for b in bits], list(range(2780, 36781, 2000)))
        self.assertEqual(report["events"][0], {"kind": "START", "t": 940})
        self.assertEqual((report["stop"], report["halt"], report["releases"]), (39580, 40524, 19))
        self.assertEqual(report["fastest_hz"], 100000)
        self.assertEqual(rows[-1]["oe"], 28)

    def test_all_bytes_all_kinds_and_target_phases(self):
        # 3 * 256 * 4 = 3072 independent reference transactions. Multiplication
        # by an odd number permutes all receive bytes; seed and every input fixed.
        for kind in ("write", "read", "write_read"):
            for byte in range(256):
                case = Transaction(kind=kind, address=8+byte%112, tx=byte, rx=(37*byte+83)%256)
                for response in (4, 5, 7, 690):
                    self.assert_pass(case, response=response)

    def test_all_ordinary_addresses(self):
        for address in range(8, 120):
            for kind in ("write", "read", "write_read"):
                self.assert_pass(Transaction(kind=kind, address=address))

    def test_nack_stops_at_each_permitted_boundary(self):
        cases = [("write", "address", 9), ("write", "data", 18),
                 ("read", "address", 9), ("write_read", "address", 9),
                 ("write_read", "data", 18), ("write_read", "read_address", 27)]
        for kind, nack, count in cases:
            _, report = self.assert_pass(Transaction(kind=kind, nack=nack))
            self.assertEqual(sum(e["kind"] == "BIT" for e in report["events"]), count)
            self.assertEqual(report["outcome"], "NACK")

    def test_stretch_at_every_release_with_reproducible_offsets(self):
        rng = random.Random(SEED)
        for kind, count in (("write", 19), ("read", 19), ("write_read", 38)):
            for release in range(1, count+1):
                delay = rng.randrange(1, 8001)
                self.assert_pass(Transaction(kind=kind), stretches={release: delay})
        # All edges stretched in a single transaction, not just isolated events.
        self.assert_pass(Transaction(), stretches={n: 1001+n%4 for n in range(1, 39)})

    def test_deadline_observation_edge_priority(self):
        self.assertEqual([observation_edge(t) for t in (202767, 202771, 202772)],
                         [202776, 202780, 202784])
        for kind, count in (("write", 19), ("read", 19), ("write_read", 38)):
            for release in range(1, count+1):
                for delay in (199987, 199991):
                    self.assert_pass(Transaction(kind=kind), stretches={release: delay})
                for delay in (199992, None):
                    self.assert_pass(Transaction(kind=kind, timeout_release=release), stretches={release: delay})

    def test_timing_minima_and_immediately_shorter_controls(self):
        case = Transaction(kind="write")
        for kw in ({"low": 940, "high": 1060}, {"low": 1200, "high": 800},
                   {"first_idle": 940}, {"start_hold": 800}, {"stop_setup": 800}, {"bus_free": 940}):
            self.assert_pass(case, **kw)
        for kw, failure in (({"low": 936, "high": 1064}, "scl_low"),
                            ({"low": 1204, "high": 796}, "scl_high"),
                            ({"first_idle": 936}, "bus_free_before_start"),
                            ({"start_hold": 796}, "start_hold"),
                            ({"stop_setup": 796}, "stop_setup"),
                            ({"bus_free": 936}, "early_outcome"),
                            ({"low": 1040, "high": 956}, "clock_frequency")):
            self.assertIn(failure, kinds(waveform(case, **kw), case))
        both = Transaction()
        self.assert_pass(both, restart_setup=940)
        self.assertIn("repeated_start_setup", kinds(waveform(both, restart_setup=936), both))

    def test_target_data_setup_and_validity_are_separate(self):
        case = Transaction(kind="read", rx=0x55)
        self.assert_pass(case, response=690)
        self.assertIn("data_valid_delay", kinds(waveform(case, response=691), case))
        # Stretch every low phase: maximum valid delay is exempt, setup remains.
        stretches = {n: 1000 for n in range(1, 20)}
        self.assert_pass(case, response=900, stretches=stretches)
        # Release later in the low period so setup, not valid-max, is isolated.
        rows = waveform(case, stretches={10: 1000})
        rise = next(e["t"] for e in assess(rows, case)["events"] if e.get("index") == 9)
        previous = next(r for r in reversed(rows) if r["t"] < rise-50)
        boundary = insert(rows, rise-51, target_oe=previous["target_oe"] ^ 2)
        boundary = insert(boundary, rise-50, target_oe=previous["target_oe"])
        self.assertEqual(kinds(boundary, case), set())
        changed = insert(rows, rise-50, target_oe=previous["target_oe"] ^ 2)
        changed = insert(changed, rise-49, target_oe=previous["target_oe"])
        self.assertIn("data_setup", kinds(changed, case))

    def test_both_drivers_must_be_open_drain(self):
        case = Transaction(kind="write")
        rows = waveform(case)
        # Active high can have exactly the correct logic value and still fail.
        bad = insert(rows, 2784, out=2, oe=30)
        bad[ next(i for i, r in enumerate(bad) if r["t"] == 2784) ]["bus"] = 3
        self.assertIn("controller_active_high", kinds(bad, case))
        bad = insert(rows, 2784, target_out=2, target_oe=2)
        self.assertIn("target_active_high", kinds(bad, case))
        bad = copy.deepcopy(rows)
        bad[10]["bus"] ^= 1
        self.assertIn("wired_and", kinds(bad, case))

    def test_wrong_program_bits_addresses_and_bit_order(self):
        case = Transaction(kind="write", tx=0x96)
        for wrong in (replace(case, tx=0x69), replace(case, address=0x53),
                      replace(case, tx=0x94)):
            self.assertIn("wire_bit", kinds(waveform(wrong), case))

    def test_wrong_ack_missing_extra_ack_and_continue_after_nack(self):
        case = Transaction(kind="read")
        rows = waveform(case)
        # ACK the final read byte instead of NACK: wrong data and ownership.
        bad = change_interval(rows, 35744, 37741, oe=30)
        self.assertTrue({"wire_bit", "sda_ownership"} & kinds(bad, case))
        case = Transaction(kind="write")
        rows = waveform(case)
        # Delete ninth pulse (18,780 rise / 19,740 fall), retaining next byte.
        bad = [r for r in rows if not 17741 <= r["t"] <= 19740]
        self.assertIn("segment_length", kinds(bad, case))
        # Add a complete extra pulse before STOP by copying a preceding pulse.
        bad = copy.deepcopy(rows)
        pulse = [dict(r, t=r["t"]+2000) for r in rows if 35740 < r["t"] <= 37740]
        for r in bad:
            if r["t"] > 37740:
                r["t"] += 2000
        bad = sorted(bad+pulse, key=lambda r: r["t"])
        self.assertIn("extra_clock", kinds(bad, case))
        rejected = replace(case, nack="address")
        self.assertIn("extra_clock", kinds(waveform(case), rejected))

    def test_sda_high_glitch_and_owner_handoff(self):
        case = Transaction(kind="write")
        rows = waveform(case)
        bad = insert(rows, 3000, oe=30)
        self.assertIn("segment_length", kinds(bad, case))
        # Same resolved zero, wrong actor starts driving it during high.
        bad = insert(rows, 5000, target_oe=2)
        self.assertIn("sda_ownership_during_high", kinds(bad, case))

    def test_stop_instead_of_repeated_start_and_incomplete_trace(self):
        expected = Transaction()
        self.assertIn("segment_length", kinds(waveform(replace(expected, kind="write")), expected))
        rows = waveform(expected)
        self.assertIn("missing_stop", kinds(rows[:20], expected))
        self.assertIn("missing_halt", kinds(rows[:-3], expected))

    def test_direction_advance_during_stretch_is_visible_even_on_flat_bus(self):
        case = Transaction(kind="write", timeout_release=1)
        rows = waveform(case, stretches={1: None})
        # Raw SCL stays low, but the controller wrongly starts another cycle.
        bad = insert(rows, 3000, oe=29)
        self.assertIn("advance_before_scl_observed", kinds(bad, case))
        bad = insert(rows, 3000, oe=30)
        self.assertIn("advance_before_scl_observed", kinds(bad, case))

    def test_target_cannot_supply_the_controllers_clock(self):
        case = Transaction(kind="write")
        bad = waveform(case)
        for row in bad:
            row["target_oe"] |= row["oe"] & 1
            row["oe"] &= ~1
        # Identical resolved wires are insufficient if the wrong device clocks.
        self.assertTrue({"scl_owner", "clock_release_count"} <= kinds(bad, case))

    def test_timeout_controls_and_bounded_release(self):
        case = Transaction(kind="write", timeout_release=1)
        rows = waveform(case, stretches={1: None})
        deadline = 202780
        early = copy.deepcopy(rows)
        for row in early:
            if row["t"] >= deadline+4:
                row["t"] -= 100
        self.assertIn("timeout_marker_deadline", kinds(early, case))
        late = copy.deepcopy(rows)
        for row in late:
            if row["t"] >= deadline+4:
                row["t"] += 68
        self.assertIn("timeout_cleanup_deadline", kinds(late, case))
        stuck = change_interval(rows, deadline, deadline+100, oe=30)
        self.assertIn("terminal_outcome_or_release", kinds(stuck, case))
        final_edge = waveform(replace(case, timeout_release=None), stretches={1: 199991})
        self.assertIn("premature_timeout", kinds(final_edge, case))

    def test_raw_result_is_not_accepted_until_successful_halt(self):
        case = Transaction(kind="read", rx=0x69)
        rows = waveform(case)
        self.assertIn("received_byte", kinds(change_interval(rows, 0, 1000000, rx=0xD3), case))
        self.assertIn("received_byte", kinds(change_interval(rows, 0, 1000000, rx_valid=0), case))
        self.assertIn("initial_stale_valid", kinds(change_interval(rows, 0, 1000000, rx_valid=1), case))
        bad = copy.deepcopy(rows)
        for row in bad:
            if row["t"] >= 37744:
                row["out"] = 4
        self.assertIn("early_outcome", kinds(bad, case))
        # A raw-valid address or partial old result is never alone acceptance.
        early_raw = copy.deepcopy(rows)
        for row in early_raw:
            if 19740 <= row["t"] < 37744:
                row.update(rx_valid=1, rx=0xD3)
        self.assertEqual(kinds(early_raw, case), set())

    def test_malformed_traces_and_intents_fail_closed(self):
        case = Transaction()
        rows = waveform(case)
        self.assertIn("empty_trace", kinds([], case))
        self.assertIn("trace_schema", kinds([{"t": 0}], case))
        self.assertIn("trace_order_or_state", kinds(rows+[rows[-1]], case))
        bad = copy.deepcopy(rows)
        bad[0]["oe"] = -1
        self.assertIn("trace_value", kinds(bad, case))
        for kw in ({"kind": "invalid"}, {"address": 0}, {"address": 120},
                   {"tx": -1}, {"rx": 256}, {"kind": "read", "nack": "data"}):
            with self.assertRaises(ValueError):
                Transaction(**kw)

    def test_reset_disable_and_loader_are_declared_aborts(self):
        case = Transaction(kind="read")
        trace = waveform(case)
        # Includes address, ACK, data, final response and STOP preparation cuts.
        for tick in (1200, 3000, 18800, 22000, 37000, 39000):
            for control in ("reset", "disable", "load"):
                rows = [dict(r, rst_n=1, ena=1, load=0, target_isolated=0)
                        for r in trace if r["t"] < tick]
                cut = dict(rows[-1], t=tick)
                if control == "reset":
                    cut.update(rst_n=0, out=0, oe=0, rx=0, rx_valid=0, state="RUN")
                elif control == "disable":
                    cut.update(ena=0)
                else:
                    cut.update(load=1, target_isolated=1, target_oe=0, out=255, oe=255)
                rows.extend([cut, dict(cut, t=tick+80)])
                result = assess_abort(rows, case, control=control, tick=tick)
                self.assertEqual(result["errors"], [], (control, tick, result))
                self.assertEqual(result["outcome"], "ABORT")
                self.assertIsNone(result["halt"])
                self.assertTrue(assess(rows, case)["errors"])
                bad = copy.deepcopy(rows)
                if control == "reset":
                    bad[-1]["rx_valid"] = 1
                    failure = "reset_effect"
                elif control == "disable":
                    bad[-1]["oe"] ^= 2
                    failure = "disable_freeze"
                else:
                    bad[-1]["target_oe"] = 2
                    failure = "loader_target_connected"
                self.assertIn(failure, {e["kind"] for e in assess_abort(bad, case, control=control, tick=tick)["errors"]})


if __name__ == "__main__":
    unittest.main()
