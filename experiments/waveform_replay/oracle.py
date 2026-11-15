# SPDX-License-Identifier: Apache-2.0
"""Check G5 public observations against the preregistered literal schedule.

No instruction decoder, assembler, RTL model or observed trace supplies the
expected waveform. ``paused=True`` checks only the deliberately paused case's
accepted-edge behavior; the ordinary wall-clock contract rejects that trace.
"""
import json
from pathlib import Path


EXPECTED = json.loads(Path(__file__).with_name('expected.json').read_bytes())
FIELDS = ('edge', 'accepted_edge', 'ena', 'raw', 'out', 'oe', 'status')


def _pins(accepted_edge, first, schedule):
    if first is None:
        return (0, 0) if accepted_edge >= EXPECTED['timeout_release_edge'] else (0, 7)
    value, enable = EXPECTED['runtime_initial']
    for offset, next_value, next_enable in schedule:
        if accepted_edge < first + offset:
            break
        value, enable = next_value, next_enable
    return value, enable


def _status(accepted_edge, first, schedule):
    """Public state/PC landmarks of the frozen 20-word SET/WAIT program.

    Word zero initializes GPIO, word one waits for the trigger, alternating
    SET/WAIT words occupy 2..17, and cleanup/HALT occupy 18/19. Event offsets
    come only from expected.json. This checks program timing even when a case
    intentionally asks the *other* waveform oracle to reject its pin trace.
    """
    if accepted_edge == 1:
        return 0x21
    if first is None:
        if accepted_edge < EXPECTED['timeout_release_edge'] - 1:
            return 0x61
        if accepted_edge == EXPECTED['timeout_release_edge'] - 1:
            return 0x32
        if accepted_edge == EXPECTED['timeout_release_edge']:
            return 0x33
        return EXPECTED['terminal_status']
    if accepted_edge < first - 1:
        return 0x61
    if accepted_edge == first - 1:
        return 0x22
    relative = accepted_edge - first
    if relative >= EXPECTED['halt_relative_edge']:
        return EXPECTED['terminal_status']
    for index, (offset, _, _) in enumerate(schedule):
        if relative == offset:
            return 0x20 | (3 + 2 * index)
        if index + 1 < len(schedule) and relative < schedule[index + 1][0]:
            if relative == schedule[index + 1][0] - 1:
                return 0x20 | (4 + 2 * index)
            return 0x60 | (3 + 2 * index)
    raise ValueError('the frozen schedule does not cover this observation')


def assess(rows, case, *, paused=False):
    """Return deterministic error dictionaries; an empty list means acceptance.

    Rows are consecutive post-rising-edge public observations with integer
    ``edge, accepted_edge, ena, raw, out, oe, status`` fields. Edges start at one;
    disabled edges retain the preceding accepted-edge count. The case must be
    a runtime case from expected.json (loader rejection has no runtime trace).
    ``case.oracle`` overrides pins only, never the executing program's status.
    """
    errors = []

    def error(kind, edge, expected, actual):
        errors.append({'kind': kind, 'edge': edge, 'expected': expected, 'actual': actual})

    if not isinstance(rows, list):
        error('trace_format', None, 'list of public observations', type(rows).__name__)
        return errors
    if not isinstance(case, dict) or 'first' not in case:
        error('case_format', None, 'frozen runtime case with first', case)
        return errors
    program = case.get('program')
    oracle = case.get('oracle', program)
    if program not in EXPECTED['events'] or oracle not in EXPECTED['events']:
        error('case_format', None, 'known program and waveform oracle', [program, oracle])
        return errors
    first = case['first']
    if first is not None and (type(first) is not int or first < 3):
        error('case_format', None, 'first is null or an integer at least three', first)
        return errors
    pauses = case.get('pause_edges', []) if paused else []
    if (not isinstance(pauses, list) or any(type(n) is not int or n < 1 for n in pauses)
            or len(set(pauses)) != len(pauses)
            or any(first is None or n <= first for n in pauses)):
        error('case_format', None, 'distinct positive post-trigger pause edges', pauses)
        return errors
    pauses = set(pauses)
    halt = (EXPECTED['timeout_halt_edge'] if first is None else
            first + EXPECTED['halt_relative_edge'])
    last = halt + EXPECTED['post_halt_edges']
    for pause in sorted(pauses):
        if pause <= last:
            last += 1
    if len(rows) != last:
        error('trace_length', None, last, len(rows))

    for edge, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            error('row_format', edge, 'public observation object', type(row).__name__)
            continue
        invalid = [field for field in FIELDS if type(row.get(field)) is not int]
        invalid += [field for field in ('raw', 'out', 'oe', 'status')
                    if type(row.get(field)) is int and not 0 <= row[field] <= 255]
        if type(row.get('ena')) is int and row['ena'] not in (0, 1):
            invalid.append('ena')
        if invalid:
            error('row_format', edge, 'integer fields and byte-valued pins/status', sorted(set(invalid)))
            continue
        if row['edge'] != edge:
            error('edge_sequence', edge, edge, row['edge'])
        accepted_edge = edge - sum(pause <= edge for pause in pauses)
        if row['accepted_edge'] != accepted_edge:
            error('accepted_edge', edge, accepted_edge, row['accepted_edge'])
        enable = int(edge not in pauses)
        if row['ena'] != enable:
            error('enable', edge, enable, row['ena'])
        raw = case.get('idle', 0)
        if 'trigger_edge' in case and edge >= case['trigger_edge']:
            raw |= 1 << case.get('trigger_pin', 7)
        if row['raw'] != raw:
            error('raw_input', edge, raw, row['raw'])
        value, output_enable = _pins(accepted_edge, first, EXPECTED['events'][oracle])
        if (row['out'], row['oe']) != (value, output_enable):
            error('waveform', edge, {'out': value, 'oe': output_enable},
                  {'out': row['out'], 'oe': row['oe']})
        status = _status(accepted_edge, first, EXPECTED['events'][program])
        if row['status'] != status:
            error('status', edge, status, row['status'])
    return errors
