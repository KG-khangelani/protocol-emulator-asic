# SPDX-License-Identifier: Apache-2.0
"""Check only the external pads reconstructed from the packed FPGA configuration."""

import gzip
import hashlib
import json
import os
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

ROOT = Path(os.environ['FPGA_UART_ROOT'])
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble, json_bytes, program_bytes
from tools.cold_load import UART_BINARY, UART_SOURCE
from tools.uart_rx_host_service import HostReader
from tools.uart_rx_oracle import Frame, expected_schedule, line_level


def reference():
    evidence = ROOT / 'evidence/E0050-powered-cold-loader'
    packed = gzip.decompress((evidence / 'uart-transcript.json.gz').read_bytes())
    receipt = json.loads((evidence / 'uart-result.json').read_bytes())
    assert receipt['status'] == 'PASS'
    assert hashlib.sha256(packed).hexdigest() == receipt['transcript_sha256'] == (
        'c660d0d69282094b6999c4b5ce83303e77c0307be5571762ec64ebb7ffb0a188')
    trace = json.loads(packed)
    data = bytes(row['expected']['uio_out'] for row in trace['loader'] if row['action'] == 'read_byte_after_edge')
    assembly = ROOT / 'programs/od128-sram-v1/uart_rx.asm'
    assert hashlib.sha256(assembly.read_bytes()).hexdigest() == UART_SOURCE
    image = assemble(assembly.read_text())
    assert data == program_bytes(image) and image['binary_sha256'] == UART_BINARY
    assert len(data) == 32 and len(trace['loader']) == 76
    return trace


def check_unowned_pads(dut, operation):
    # A pad disconnected from both outside drivers directly exposes Z. With
    # an outside source attached, equal data alone cannot establish ownership.
    target = operation['uio_oe']
    if not isinstance(target, int):
        return  # Direction before the first reset edge is unspecified.
    external = operation['host_mask'] | operation['peer_drive']
    bits = str(dut.uio.value)[::-1].upper()
    for index, value in enumerate(bits):
        if not (external >> index) & 1:
            assert (value != 'Z') == bool((target >> index) & 1), (operation, bits, index)


async def replay_loader(dut, trace, quarter_ps, fault=None):
    rows = trace['loader']
    edge = 0
    verified = []
    handoff = []
    dut.clk.value = 0
    dut.peer_level.value = 1
    for operation in trace['operations']:
        row = rows[edge] if edge < len(rows) else None
        dut.rst_n.value = operation['rst_n']
        dut.ui_in.value = operation['ui_in']
        dut.host_mask.value = operation['host_mask']
        dut.peer_connected.value = int(bool(operation['peer_drive']))
        if operation['host_mask']:
            data = row['raw']
            if fault == 'damaged-byte' and row['action'] == 'write_byte' and row['ui_in'] == 0xc1:
                data ^= 1
            dut.host_data.value = data
        await Timer(2, unit='ns')
        if operation['operation'] == 'clock-once':
            await Timer(2 * quarter_ps, unit='ps')  # loader low phase
            dut.clk.value = 1
            await Timer(2 * quarter_ps, unit='ps')
            dut.clk.value = 0
            await Timer(2, unit='ns')
            edge += 1
            if row['action'] == 'read_byte_after_edge' and fault == 'opposed-peer' and row['ui_in'] == 0x81:
                # Two opposed sources are modeled only in this digital control.
                dut.peer_connected.value = 1
                await Timer(2, unit='ns')
                bus = str(dut.uio.value).upper()
                assert bus == '000000X0', bus
                return {'rejected': 'opposed drivers on UIO1', 'edge': edge, 'pads': bus}
            expected = row['expected']
            if 'uo_out' in expected:
                assert int(dut.uo_out.value) == expected['uo_out'], (edge, row)
            if 'uio_out' in expected:
                actual = int(dut.uio.value)
                if actual != expected['uio_out']:
                    assert fault == 'damaged-byte' and row['ui_in'] == 0x81 and actual == 1 and expected['uio_out'] == 0
                    return {'rejected': 'byte readback', 'edge': edge, 'actual': actual, 'expected': expected['uio_out']}
                if row['action'] == 'read_byte_after_edge':
                    verified.append(actual)
        assert edge == operation['rising_edges']
        check_unowned_pads(dut, operation)
        if operation['operation'] == 'select' and edge == len(rows):
            status = int(dut.uo_out.value)
            handoff.append([edge, operation['ui_in'], status])
    assert not fault and edge == 76 and handoff == [[76, 0x67, 0x22], [76, 0, 0x20]]
    assert hashlib.sha256(bytes(verified)).hexdigest() == UART_BINARY
    return {'loader_edges': edge, 'readback_bytes': len(verified), 'readback_sha256': UART_BINARY, 'handoff': handoff}


async def read_output(dut, selector):
    dut.ui_in.value = selector
    await Timer(2, unit='ps')
    return int(dut.uo_out.value)


async def receive(dut, quarter_ps, bad_stop):
    frames = [Frame(0x96, stop=0 if bad_stop else 1), Frame(0x69)]
    schedule = expected_schedule(period=434, start_quarter=17)
    terminal_edge = schedule['checked_stop'][0] if bad_stop else schedule['halt']
    terminal = 0xe6 if bad_stop else 0xa7
    reader = HostReader(period=434, poll_gap=4338, read_latency=2)
    assert await read_output(dut, 0x63) == 0
    assert await read_output(dut, 0) == 0x20
    first_tick = None
    for n in range(1, terminal_edge + reader.gap + reader.latency + 1):
        for q in (4*n-2, 4*n-1):
            dut.peer_level.value = line_level(q, frames)
            await Timer(quarter_ps, unit='ps')
        wire = line_level(4*n, frames)
        dut.peer_level.value = wire
        await Timer(1, unit='ps')
        assert str(dut.uio.value)[-2] == str(wire), ('RX pad', n, str(dut.uio.value))
        dut.clk.value = 1
        tick = int(get_sim_time(unit='ps'))
        if first_tick is None:
            first_tick = tick
        assert tick == first_tick + (n-1)*4*quarter_ps
        await Timer(1, unit='ns')
        status = int(dut.uo_out.value)
        if n < terminal_edge:
            assert status >> 6 < 2, ('premature terminal', n, status)
        else:
            assert status == terminal, ('terminal', n, status)
        requests = reader.requests(n)
        if requests:
            valid = await read_output(dut, 0x63)
            data = await read_output(dut, 0x62) if any(r != 'poll' for r in requests) else None
            await read_output(dut, 0)
            reader.observe(n, requests, status, valid, data)
        await Timer(quarter_ps - 1 - (int(get_sim_time(unit='ps')) - tick), unit='ps')
        dut.peer_level.value = line_level(4*n+1, frames)
        await Timer(quarter_ps, unit='ps')
        dut.clk.value = 0
        if reader.accepted is not None or reader.rejected:
            assert n >= terminal_edge
            break
    if bad_stop:
        assert reader.rejected == 'not-ready/fault' and reader.accepted is None
    else:
        assert reader.accepted == (0x96, 0x69) and reader.rejected is None
    return {'accepted': reader.accepted, 'rejected': reader.rejected, 'terminal': f'{status:02X}',
            'terminal_edge': terminal_edge, 'service_edge': n, 'host_events': reader.events}


@cocotb.test()
async def package_handoff(dut):
    trace = reference()
    quarter = int(1_000_000 / (4 * float(os.environ['FPGA_UART_MHZ'])))
    dut.minimum_period_ps.value = 4 * quarter
    observations = {}
    for fault in ('damaged-byte', 'opposed-peer'):
        observations[fault] = await replay_loader(dut, trace, quarter, fault)
    for name, bad_stop in (('two-frames', False), ('bad-stop', True)):
        load = await replay_loader(dut, trace, quarter)
        observations[name] = {**load, **await receive(dut, quarter, bad_stop)}
    await Timer(1, unit='ps')
    shortest = int(dut.shortest_period_ps.value)
    edges = int(dut.observed_edges.value)
    assert shortest == 4 * quarter
    expected_edges = observations['damaged-byte']['edge'] + observations['opposed-peer']['edge']
    for name in ('two-frames', 'bad-stop'):
        expected_edges += observations[name]['loader_edges'] + observations[name]['service_edge']
    assert edges == expected_edges
    observations['clock'] = {'required_minimum_ps': 4 * quarter, 'shortest_observed_ps': shortest,
                             'observed_rising_edges': edges}
    (Path(os.environ['FPGA_UART_OUT'])/'observations.json').write_bytes(json_bytes(observations))
