# SPDX-License-Identifier: Apache-2.0
"""Execute assembled artifacts through public pins and independent wire oracles."""
import copy
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
from test import edge, initialise, uart_tx_level
from test_uart_rx_public import drive_rx, runtime_snapshot, host_observer, finish_host
from tools.uart_rx_oracle import Frame, expected_schedule
from tools.uart_rx_host_service import HostReader
from tools.spi_four_mode_oracle import timing, raw_at, assess as assess_spi
from tools.i2c_oracle import Transaction, assess as assess_i2c
from experiments.i2c.target import Target
from experiments.i2c.public_bus import run_bus

BUILT = Path(os.environ['G3_PROGRAM_BUILD'])
OUT = Path(os.environ['G3_PROGRAM_RECORDS'])
SOURCES = ROOT / 'programs/od128-sram-v1'


def image(name):
    result = json.loads((BUILT / name / 'program.json').read_bytes())
    assert program_bytes(result) == (BUILT / name / 'program.bin').read_bytes()
    assert result == assemble((SOURCES / (name + '.asm')).read_text(encoding='utf-8'))
    return result


def record(name, group, rows, **details):
    raw = (json.dumps(rows, sort_keys=True, separators=(',', ':')) + '\n').encode()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (name + '.json.gz')
    assert not path.exists(), name
    path.write_bytes(gzip.compress(raw, mtime=0))
    item = {'name': name, 'group': group, 'trace_sha256': hashlib.sha256(raw).hexdigest(),
            'observations': len(rows), **details}
    with (OUT / 'records.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(item, sort_keys=True) + '\n')


class LoadMismatch(ValueError):
    pass


async def apply_plan(dut, plan):
    initialise(dut)
    observations = []
    for index, step in enumerate(plan['steps']):
        dut.ui_in.value = step['ui_in']
        dut.uio_in.value = step['uio_in']
        await edge(dut, rst_n=step['rst_n'], ena=step['ena'])
        actual = {port: int(getattr(dut, port).value) for port in step['expected']}
        if actual != step['expected']:
            raise LoadMismatch(f"step {index} {step['action']}: observed {actual}, expected {step['expected']}")
        if step['host_drives_uio'] and actual.get('uio_oe', 0):
            raise LoadMismatch('shared pin ownership conflict')
        observations.append({'step': index, 'action': step['action'], **actual})
    return observations


async def prepare(dut, name, *, override=None, payloads=None):
    program = image(name) if override is None else override
    plan = load_plan(program, payloads=payloads)
    if override is None and payloads is None:
        assert plan == json.loads((BUILT / name / 'load-plan.json').read_bytes())
    await apply_plan(dut, plan)
    return program


async def snapshot(dut, number):
    before = (int(dut.uio_out.value), int(dut.uio_oe.value))
    status, values, spent = await runtime_snapshot(dut, (2, 3), held_address=0)
    assert before == (int(dut.uio_out.value), int(dut.uio_oe.value))
    return {'edge': number, 'out': before[0], 'oe': before[1],
            'state': ('RUN', 'WAIT', 'HALT', 'FAULT')[status >> 6],
            'rx': values[0], 'rx_valid': values[1]}, spent


@cocotb.test()
async def assembled_loader_controls(dut):
    assert not hasattr(dut, 'engine_instruction'), 'this suite must expose only the public top'
    for length in (1, 8, 9, 128):
        source = '.target od128-sram-v1\n' + ''.join(
            f'SET mask=255 value={n} oe=1\n' for n in range(length - 1)) + 'HALT\n'
        program = assemble(source)
        rows = await apply_plan(dut, load_plan(program))
        for n in range(length):
            await edge(dut)
            status = int(dut.uo_out.value)
            assert status >> 6 == (2 if n == length - 1 else 0)
            expected = max(0, n - 1) if n == length - 1 else n
            assert int(dut.uio_out.value) == expected
            dut.ui_in.value = 0x66
            await Timer(1, unit='ps')
            pc = int(dut.uo_out.value)
            assert pc == min(n + 1, length - 1)
            dut.ui_in.value = 0
            rows.append({'execution_edge': n + 1, 'out': int(dut.uio_out.value), 'pc': pc, 'status': status})
        record(f'load-{length}', 'loader', rows, expected_acceptance=True)
    for kind in ('interface', 'readback'):
        plan = load_plan(image('i2c_write_read'))
        if kind == 'interface':
            plan['steps'][1]['expected']['uo_out'] = 0x21
        else:
            last = [s for s in plan['steps'] if s['action'] == 'read_byte_after_edge'][-1]
            last['expected']['uio_out'] ^= 1
        try:
            await apply_plan(dut, plan)
        except LoadMismatch as error:
            dut.ui_in.value = 0
            await Timer(1, unit='ps')
            assert not int(dut.uo_out.value) & 0x20, 'mismatch must stop before commit/run'
            record('reject-' + kind, 'loader', [{'error': str(error)}], expected_acceptance=False, rejected=True)
        else:
            assert False, 'invalid loader expectation was not rejected'
    # A good reload recovers after the failed readback and changes observable output.
    first = assemble('.target od128-sram-v1\nSET mask=1 value=1 oe=1\nHALT\n')
    second = assemble('.target od128-sram-v1\nSET mask=1 value=0 oe=1\nHALT\n')
    rows = []
    for program, expected in ((first, 1), (second, 0)):
        await apply_plan(dut, load_plan(program))
        await edge(dut)
        assert int(dut.uio_out.value) == expected
        await edge(dut)
        assert int(dut.uo_out.value) >> 6 == 2
        rows.append({'out': int(dut.uio_out.value), 'oe': int(dut.uio_oe.value)})
    record('reload-after-rejection', 'loader', rows, expected_acceptance=True)


@cocotb.test()
async def assembled_uart_examples(dut):
    for name, payloads, wrong_period in (
            ('uart-tx-default', None, False), ('uart-tx-corners', {'TX0': 0, 'TX1': 255}, False),
            ('uart-tx-wrong-period', None, True)):
        override = None
        if wrong_period:
            source = (SOURCES / 'uart_tx.asm').read_text(encoding='utf-8')
            override = assemble(source.replace('.const PERIOD 434', '.const PERIOD 436'))
        program = await prepare(dut, 'uart_tx', override=override, payloads=payloads)
        data = payloads or program['payloads']
        rows, errors = [], []
        for n in range(1, 3 + 20 * 434 + 1):
            await edge(dut)
            actual = {'edge': n, 'out': int(dut.uio_out.value), 'oe': int(dut.uio_oe.value),
                      'status': int(dut.uo_out.value)}
            rows.append(actual)
            if actual['out'] & 1 != uart_tx_level(n, 434, data['TX0'], data['TX1']) or actual['oe'] & 3 != 1:
                errors.append(n)
        if rows[-1]['status'] != 0xA7:
            errors.append(rows[-1]['edge'])
        record(name, 'uart_tx', rows, expected_acceptance=not wrong_period,
               accepted=not errors, first_error_edges=errors[:8], binary_sha256=program['binary_sha256'])
        assert bool(errors) == wrong_period
    for bad_stop in (False, True):
        program = await prepare(dut, 'uart_rx')
        dut.ui_in.value = 0x64
        await Timer(1, unit='ns')
        reader = HostReader(period=434, poll_gap=4338, read_latency=2)
        host = host_observer(reader)
        rows = []

        async def observe(dut, n):
            spent = await host(dut, n)
            before = (int(dut.uio_out.value), int(dut.uio_oe.value))
            status, values, extra = await runtime_snapshot(dut, (2, 3))
            rows.append({'edge': n, 'out': before[0], 'oe': before[1], 'status': status,
                         'rx': values[0], 'rx_valid': values[1]})
            return spent + extra

        expected = expected_schedule(period=434, start_quarter=17)
        terminal = expected['checked_stop'][0] if bad_stop else expected['halt']
        await drive_rx(dut, [Frame(0x96, stop=0 if bad_stop else 1), Frame(0x69)],
                       period=434, start_quarter=17, end_edge=terminal,
                       terminal=0xE6 if bad_stop else 0xA7, observer=observe)
        await finish_host(dut, reader, observe, terminal)
        assert (reader.accepted is None and bool(reader.rejected)) if bad_stop else reader.accepted == (0x96, 0x69)
        record('uart-rx-bad-stop' if bad_stop else 'uart-rx-host-delivery', 'uart_rx', rows,
               expected_acceptance=not bad_stop, accepted=reader.accepted is not None,
               host_events=reader.events, host_rejected=reader.rejected,
               binary_sha256=program['binary_sha256'])


async def spi_case(dut, name, mode, order, *, profile='held', wrong_program=False, response=96):
    example = f'spi_mode{mode}_{"msb" if order else "lsb"}'
    override = None
    if wrong_program:
        source = (SOURCES / (example + '.asm')).read_text(encoding='utf-8')
        override = assemble(source.replace('delay=HALF-2', 'delay=HALF-3', 1))
    program = await prepare(dut, example, override=override)
    schedule = timing(mode, 2 if mode & 1 else 3)
    trace = [{'edge': 0, 'out': 0, 'oe': 0, 'miso': 1, 'rx': 0, 'rx_valid': 0, 'state': 'RUN'}]
    dut.ena.value = 1
    for n in range(1, schedule['halt'] + 1):
        await Timer(9999, unit='ps')
        raw = raw_at(n, schedule, 0x69, order, profile, [response] * 8)
        dut.uio_in.value = raw << 1
        await Timer(1, unit='ps')
        dut.clk.value = 1
        await Timer(1, unit='ps')
        row, spent = await snapshot(dut, n)
        row['miso'] = raw
        trace.append(row)
        await Timer(9999 - spent, unit='ps')
        dut.clk.value = 0
    errors = assess_spi(trace, schedule, 0x96, 0x69, order, [n + 24 for n in schedule['sample']])
    expected_acceptance = profile == 'held' and not wrong_program
    kinds = sorted({item['kind'] for item in errors})
    record(name, 'spi', trace, mode=mode, order=order, profile=profile,
           expected_acceptance=expected_acceptance, accepted=not errors, errors=kinds,
           binary_sha256=program['binary_sha256'])
    assert (not errors) == expected_acceptance, (name, errors[:3])
    if profile == 'edge_only':
        assert 'received_byte' in kinds


@cocotb.test()
async def assembled_spi_examples(dut):
    for mode in range(4):
        for order in (0, 1):
            for response in (1, 96):
                await spi_case(dut, f'spi-m{mode}-o{order}-held-{response}', mode, order, response=response)
            await spi_case(dut, f'spi-m{mode}-o{order}-edge-only', mode, order, profile='edge_only')
    await spi_case(dut, 'spi-wrong-sample-delay', 1, 1, wrong_program=True)


async def i2c_case(dut, name, case, *, stretches=None, wrong_program=None):
    example = 'i2c_' + case.kind
    override = None
    if wrong_program:
        source = (SOURCES / (example + '.asm')).read_text(encoding='utf-8')
        if wrong_program == 'active-high':
            source = source.replace('drive=open_drain', 'drive=push_pull', 1)
        elif wrong_program == 'late-timeout':
            source = source.replace('.const CLOCK_TIMEOUT 49999', '.const CLOCK_TIMEOUT 50000')
        else:
            raise ValueError(wrong_program)
        override = assemble(source)
    program = await prepare(dut, example, override=override)
    target = Target(case, response=690, stretches=stretches)
    rows = await run_bus(dut, target, bound_ticks=8000000, extended_pc=True)
    initial = next(i for i, row in enumerate(rows) if row['oe'] == 28 and row['out'] == 0 and row['bus'] == 3)
    assert not any(row['out'] & row['oe'] & 3 for row in rows[:initial+1])
    offset = rows[initial]['t']
    trace = [dict(row, t=row['t']-offset) for row in rows[initial:]]
    report = assess_i2c(trace, case)
    errors = sorted({item['kind'] for item in report['errors']})
    record(name, 'i2c', trace, kind=case.kind, expected_acceptance=not wrong_program,
           accepted=not errors, errors=errors, outcome=report['outcome'], fastest_hz=report['fastest_hz'],
           binary_sha256=program['binary_sha256'])
    assert bool(errors) == bool(wrong_program), (name, report['errors'][:5])
    if not wrong_program:
        assert report['outcome'] == case.outcome


@cocotb.test()
async def assembled_i2c_examples(dut):
    for kind in ('write', 'read', 'write_read'):
        await i2c_case(dut, kind + '-normal', Transaction(kind=kind))
        await i2c_case(dut, kind + '-stretch', Transaction(kind=kind), stretches={4: 1001})
        await i2c_case(dut, kind + '-nack', Transaction(kind=kind, nack='address'))
        await i2c_case(dut, kind + '-timeout', Transaction(kind=kind, timeout_release=4), stretches={4: None})
    await i2c_case(dut, 'write-nack-data', Transaction(kind='write', nack='data'))
    await i2c_case(dut, 'write-read-nack-read-address', Transaction(nack='read_address'))
    await i2c_case(dut, 'write-read-final-edge', Transaction(), stretches={4: 199991})
    await i2c_case(dut, 'write-read-one-tick-late', Transaction(timeout_release=4), stretches={4: 199992})
    await i2c_case(dut, 'i2c-active-high-control', Transaction(), wrong_program='active-high')
    await i2c_case(dut, 'i2c-late-timeout-control', Transaction(timeout_release=4),
                   stretches={4: 199992}, wrong_program='late-timeout')
