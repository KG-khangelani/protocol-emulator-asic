# SPDX-License-Identifier: Apache-2.0
"""G5 experiments on the public top: load bytes, read them back, observe pins."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble, load_plan, program_bytes
from experiments.waveform_replay.oracle import assess
from test import edge, initialise

SOURCES = ROOT / 'experiments/waveform_replay'
CONTRACT = json.loads((SOURCES / 'expected.json').read_bytes())
BUILT = Path(os.environ['G5_PROGRAM_BUILD'])
OUT = Path(os.environ['G5_RECORDS'])


class LoadMismatch(ValueError):
    def __init__(self, message, rows):
        super().__init__(message)
        self.rows = rows


def image(case):
    name = case['program']
    source = (SOURCES / (name + '.asm')).read_text(encoding='utf-8')
    result = json.loads((BUILT / name / 'program.json').read_bytes())
    assert result == assemble(source)
    assert program_bytes(result) == (BUILT / name / 'program.bin').read_bytes()
    if case.get('mutation') == 'uncompensated':
        old = 'WAIT cycles=5\nSET mask=7 value=7'
        assert source.count(old) == 1
        source = source.replace(old, 'WAIT cycles=7\nSET mask=7 value=7')
        result = assemble(source)
    elif case.get('mutation') == 'missing_release':
        old = 'SET mask=255 value=0 oe=0'
        assert source.count(old) == 1
        result = assemble(source.replace(old, 'SET mask=255 value=0 oe=7'))
    return result


async def load(dut, program, case, *, corrupt=False):
    assert not hasattr(dut, 'engine_instruction'), 'must exercise the public top'
    initialise(dut)
    plan = load_plan(program)
    write_index = 0
    rows = []
    for index, step in enumerate(plan['steps']):
        raw = step['uio_in']
        if step['action'] == 'write_byte':
            if corrupt and write_index == 40:
                raw ^= 1  # Corrupt the actual loaded byte, not the expectation.
            write_index += 1
        if step['action'] == 'flush_idle':
            raw = case.get('idle', 0)
        dut.ui_in.value = step['ui_in']
        dut.uio_in.value = raw
        await edge(dut, rst_n=step['rst_n'], ena=step['ena'])
        actual = {port: int(getattr(dut, port).value) for port in step['expected']}
        row = {'step': index, 'action': step['action'], 'raw': raw,
               'ui_in': step['ui_in'], 'rst_n': step['rst_n'], 'ena': step['ena'],
               'host_drives_uio': step['host_drives_uio'], 'expected': step['expected'],
               'actual': actual}
        rows.append(row)
        if actual != step['expected']:
            raise LoadMismatch(f'public readback mismatch at step {index}', rows)
        if step['host_drives_uio'] and int(dut.uio_oe.value):
            raise LoadMismatch(f'bus contention at step {index}', rows)
    assert write_index == 80
    return rows


async def runtime(dut, case):
    first = case['first']
    halt = CONTRACT['timeout_halt_edge'] if first is None else first + CONTRACT['halt_relative_edge']
    if case.get('mutation') == 'uncompensated':
        halt += 2
    halt += len(case.get('pause_edges', []))
    rows = []
    accepted = 0
    raw = case.get('idle', 0)
    dut.rst_n.value = 1
    dut.ui_in.value = 0
    for n in range(1, halt + CONTRACT['post_halt_edges'] + 1):
        enabled = int(n not in case.get('pause_edges', []))
        dut.ena.value = enabled
        phase = case.get('phase_ps', 5000)
        await Timer(phase, unit='ps')
        if n == case.get('trigger_edge'):
            raw = 1 << case.get('trigger_pin', 7)
            dut.uio_in.value = raw
        if n == case.get('pulse_edge'):
            # Entire pulse lies between rising edges; no sampled high.
            assert phase == 5000
            # The phase timer above placed us 5 ns after the falling edge;
            # use a 2 ns pulse, ending 3 ns before this rising edge.
            dut.uio_in.value = 128
            await Timer(2000, unit='ps')
            dut.uio_in.value = 0
            await Timer(3000, unit='ps')
        else:
            await Timer(10000 - phase, unit='ps')
        dut.clk.value = 1
        await Timer(1, unit='ps')
        accepted += enabled
        rows.append({'edge': n, 'accepted_edge': accepted, 'ena': enabled,
                     'raw': int(dut.uio_in.value), 'out': int(dut.uio_out.value),
                     'oe': int(dut.uio_oe.value), 'status': int(dut.uo_out.value)})
        await Timer(9999, unit='ps')
        dut.clk.value = 0
    return rows


def record(case, program, loader, rows, errors, **details):
    trace = {'loader': loader, 'runtime': rows}
    raw = (json.dumps(trace, sort_keys=True, separators=(',', ':')) + '\n').encode()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (case['name'] + '.json.gz')
    assert not path.exists(), 'never overwrite a prior case'
    path.write_bytes(gzip.compress(raw, mtime=0))
    item = {'name': case['name'], 'group': case['group'],
            'expected_acceptance': case['accepted'], 'accepted': not errors,
            'errors': errors, 'trace_sha256': hashlib.sha256(raw).hexdigest(),
            'observations': len(loader) + len(rows),
            'binary_sha256': program['binary_sha256'], **details}
    with (OUT / 'records.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(item, sort_keys=True) + '\n')
    return item


async def run_case(dut, case):
    program = image(case)
    loader = await load(dut, program, case)
    rows = await runtime(dut, case)
    errors = assess(rows, case)
    extra = {}
    if case.get('pause_edges'):
        extra['paused_schedule_errors'] = assess(rows, case, paused=True)
    result = record(case, program, loader, rows, errors, **extra)
    assert result['accepted'] == case['accepted'], (case['name'], errors[:8])
    if case.get('pause_edges'):
        assert not extra['paused_schedule_errors'], extra
    if case['name'] == 'fault-vs-control':
        assert [(e['kind'], e['edge']) for e in errors] == [('waveform', 31), ('waveform', 32)], errors
    return rows


@cocotb.test()
async def replay_waveforms(dut):
    observed = {}
    for case in CONTRACT['cases']:
        if case['group'] == 'waveform':
            observed[case['name']] = await run_case(dut, case)
    control, fault = observed['control-phase-middle'], observed['fault-phase-middle']
    differences = [a['edge'] for a, b in zip(control, fault)
                   if (a['out'], a['oe']) != (b['out'], b['oe'])]
    assert differences == [31, 32], differences


@cocotb.test()
async def replay_falsification(dut):
    for case in CONTRACT['cases']:
        if case['group'] == 'falsification':
            await run_case(dut, case)


@cocotb.test()
async def replay_loader(dut):
    cases = [case for case in CONTRACT['cases'] if case['group'] == 'loader']
    bad, good = cases
    program = image(bad)
    try:
        await load(dut, program, bad, corrupt=True)
    except LoadMismatch as error:
        dut.ui_in.value = 0
        await Timer(1, unit='ps')
        assert not int(dut.uo_out.value) & 0x20, 'must reject before commit/run'
        assert error.rows[-1]['action'] == 'read_byte_after_edge'
        assert len([r for r in error.rows if r['action'] == 'write_byte']) == 80
        assert error.rows[-1]['expected']['uio_out'] ^ error.rows[-1]['actual']['uio_out'] == 1
        record(bad, program, error.rows, [], [{'kind': 'readback_mismatch'}], rejected=True)
    else:
        raise AssertionError('corrupted actual loaded byte was accepted')
    # The previous failed load left the device uncommitted. The ordinary host
    # reset/load/readback sequence must recover and reproduce the full trace.
    await run_case(dut, good)
