# SPDX-License-Identifier: Apache-2.0
"""Falsify the literal G5 checker using independently written public fixtures."""
import copy
import unittest

from experiments.waveform_replay.oracle import EXPECTED, assess


CASES = {case['name']: case for case in EXPECTED['cases']}

# Hand-reviewed absolute edge intervals for the normal control. These fixtures
# do not call the checker to obtain expected values or inspect assembled words.
CONTROL = [
    (1, 1, 0, 7, 0x21), (2, 9, 0, 7, 0x61), (10, 10, 0, 7, 0x22),
    (11, 11, 1, 7, 0x23), (12, 12, 1, 7, 0x63), (13, 13, 1, 7, 0x24),
    (14, 14, 3, 7, 0x25), (15, 17, 3, 7, 0x65), (18, 18, 3, 7, 0x26),
    (19, 19, 2, 7, 0x27), (20, 22, 2, 7, 0x67), (23, 23, 2, 7, 0x28),
    (24, 24, 6, 7, 0x29), (25, 29, 6, 7, 0x69), (30, 30, 6, 7, 0x2A),
    (31, 31, 7, 7, 0x2B), (32, 38, 7, 7, 0x6B), (39, 39, 7, 7, 0x2C),
    (40, 40, 3, 7, 0x2D), (41, 46, 3, 7, 0x6D), (47, 47, 3, 7, 0x2E),
    (48, 48, 1, 7, 0x2F), (49, 55, 1, 7, 0x6F), (56, 56, 1, 7, 0x30),
    (57, 57, 0, 7, 0x31), (58, 61, 0, 7, 0x71), (62, 62, 0, 7, 0x32),
    (63, 63, 0, 0, 0x33), (64, 72, 0, 0, 0xB3),
]
TIMEOUT = [(1, 1, 0, 7, 0x21), (2, 33, 0, 7, 0x61),
           (34, 34, 0, 7, 0x32), (35, 35, 0, 0, 0x33), (36, 44, 0, 0, 0xB3)]


def fixture(intervals):
    return [{'edge': edge, 'accepted_edge': edge, 'ena': 1,
             'raw': 128 if edge >= 8 else 0, 'out': out, 'oe': oe, 'status': status}
            for start, end, out, oe, status in intervals for edge in range(start, end + 1)]


def control():
    return fixture(CONTROL)


def fault():
    rows = control()
    for edge in range(25, 32):
        rows[edge - 1].update(out=6, status=0x69)
    rows[31].update(out=6, status=0x2A)
    rows[32].update(out=7, status=0x2B)
    return rows


class WaveformReplayOracleTests(unittest.TestCase):
    def assert_rejected(self, rows, kind, case='control-phase-middle'):
        errors = assess(rows, CASES[case])
        self.assertIn(kind, {error['kind'] for error in errors}, errors)
        return errors

    def test_control_and_fault_match_independent_fixtures(self):
        for name, rows in (('control-phase-early', control()), ('control-phase-middle', control()),
                           ('control-phase-late', control()), ('fault-phase-early', fault()),
                           ('fault-phase-middle', fault()), ('fault-phase-late', fault()),
                           ('reload-after-rejection', control())):
            with self.subTest(case=name):
                self.assertEqual(assess(rows, CASES[name]), [])

    def test_wrong_fault_oracle_rejects_only_selected_two_edges(self):
        errors = assess(fault(), CASES['fault-vs-control'])
        self.assertEqual([(error['kind'], error['edge']) for error in errors],
                         [('waveform', 31), ('waveform', 32)])
        self.assertEqual([error['actual']['out'] for error in errors], [6, 6])
        self.assertEqual([error['expected']['out'] for error in errors], [7, 7])

    def test_boundary_and_already_high_launches(self):
        for name, rows in (('control-already-high', control()), ('fault-already-high', fault()),
                           ('control-last-trigger', control()), ('fault-last-trigger', fault())):
            case = CASES[name]
            first = case['first']
            before = fixture([(1, 1, 0, 7, 0x21)])
            if first > 3:
                before += fixture([(2, first - 2, 0, 7, 0x61)])
            before += fixture([(first - 1, first - 1, 0, 7, 0x22)])
            body = copy.deepcopy(rows[10:])
            for row in body:
                row['edge'] += first - 11
                row['accepted_edge'] = row['edge']
            result = before + body
            for row in result:
                row['raw'] = 128 if first == 3 or row['edge'] >= 32 else 0
            with self.subTest(case=name):
                self.assertEqual(assess(result, case), [])

    def test_all_timeout_shapes_release_and_halt(self):
        for name in ('control-no-trigger', 'fault-no-trigger', 'control-late-trigger',
                     'control-wrong-trigger-pin', 'control-unsampled-pulse'):
            rows = fixture(TIMEOUT)
            case = CASES[name]
            for row in rows:
                row['raw'] = ((1 << case.get('trigger_pin', 7))
                              if row['edge'] >= case.get('trigger_edge', 999) else 0)
            with self.subTest(case=name):
                self.assertEqual(assess(rows, case), [])

    def test_changed_edge_and_incorrect_fault_compensation(self):
        rows = fault()
        rows[39]['out'] = 7  # The r29 falling edge must remain at wall40.
        errors = self.assert_rejected(rows, 'waveform', 'fault-phase-middle')
        self.assertEqual([(error['kind'], error['edge']) for error in errors], [('waveform', 40)])

    def test_missing_duplicate_and_extra_records(self):
        rows = control()
        rows.pop(29)
        self.assert_rejected(rows, 'trace_length')
        self.assert_rejected(rows, 'edge_sequence')
        rows = control()
        rows.insert(30, copy.deepcopy(rows[29]))
        self.assert_rejected(rows, 'trace_length')
        self.assert_rejected(rows, 'edge_sequence')
        rows = control()
        rows.append(dict(rows[-1], edge=73, accepted_edge=73))
        self.assert_rejected(rows, 'trace_length')

    def test_missing_cleanup_and_unused_pin_ownership(self):
        rows = control()
        for row in rows[62:]:
            row['oe'] = 7
        self.assert_rejected(rows, 'waveform', 'missing-release')
        rows = control()
        rows[27]['oe'] |= 128
        self.assert_rejected(rows, 'waveform')
        rows = control()
        rows[27]['out'] |= 32
        self.assert_rejected(rows, 'waveform')

    def test_post_halt_activity_and_short_capture(self):
        rows = control()
        rows[-1]['out'] = 1
        self.assert_rejected(rows, 'waveform')
        self.assert_rejected(control()[:-1], 'trace_length')

    def test_status_ready_pc_and_premature_terminal(self):
        for edge, status in ((5, 0x41), (20, 0xB3), (64, 0xB2), (72, 0xF3)):
            rows = control()
            rows[edge - 1]['status'] = status
            with self.subTest(edge=edge):
                self.assert_rejected(rows, 'status')

    def test_disabled_edges_stretch_wall_time_but_preserve_accepted_schedule(self):
        rows = control()
        paused = []
        for row in rows:
            if row['edge'] == 20:
                paused += [dict(rows[18], edge=20, accepted_edge=19, ena=0),
                           dict(rows[18], edge=21, accepted_edge=19, ena=0)]
            paused.append(dict(row, edge=row['edge'] + (2 if row['edge'] >= 20 else 0)))
        case = CASES['paused-wall-clock']
        self.assertEqual(assess(paused, case, paused=True), [])
        kinds = {error['kind'] for error in assess(paused, case)}
        self.assertTrue({'trace_length', 'enable', 'accepted_edge', 'waveform', 'status'} <= kinds)

    def test_wrong_raw_input_and_accepted_counter(self):
        rows = control()
        rows[7]['raw'] = 0
        self.assert_rejected(rows, 'raw_input')
        rows = control()
        rows[20]['accepted_edge'] -= 1
        self.assert_rejected(rows, 'accepted_edge')

    def test_malformed_observations_fail_closed(self):
        for invalid in (None, True, 256, -1, '7'):
            rows = control()
            rows[3]['oe'] = invalid
            with self.subTest(invalid=invalid):
                self.assert_rejected(rows, 'row_format')
        rows = control()
        del rows[3]['status']
        self.assert_rejected(rows, 'row_format')
        self.assertEqual(assess(None, CASES['control-phase-middle'])[0]['kind'], 'trace_format')


if __name__ == '__main__':
    unittest.main()
