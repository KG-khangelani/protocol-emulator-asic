# SPDX-License-Identifier: Apache-2.0
"""Connect the archived public suites to the product controller and exercise failed handoffs."""

import json
import os
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'test'), str(ROOT)]
import test_program_examples_public as g3
import test_waveform_replay_public as g5
from tools.assembler import json_bytes, load_plan
from tools.cold_load import UART_BINARY
from tools.host_transport.controller import TransportError, cold_load
from tools.host_transport.digital import DigitalPins


class DamagedWrite(DigitalPins):
    def __init__(self, dut, index, **kwargs):
        super().__init__(dut, **kwargs)
        self.index = index
        self.writes = 0

    async def drive_host(self, byte):
        if self.value('ui_in') & 0xe0 == 0xc0:
            if self.writes == self.index:
                byte ^= 1
            self.writes += 1
        await super().drive_host(byte)


async def load_g3(dut, plan):
    pins = DigitalPins(dut, peer_mask=2 if plan['binary_sha256'] == UART_BINARY else 0)
    try:
        rows = await cold_load(pins, plan)
    except TransportError as error:
        raise g3.LoadMismatch(str(error)) from error
    return [{'step': row['step'], 'action': row['action'], **row['actual']} for row in rows]


async def load_g5(dut, program, case, *, corrupt=False):
    pins = DamagedWrite(dut, 40) if corrupt else DigitalPins(dut)
    try:
        return await cold_load(pins, load_plan(program, idle_inputs=case.get('idle', 0)))
    except TransportError as error:
        raise g5.LoadMismatch(str(error), error.rows) from error


# Replace only the loaders. The original program builders, wire stimuli,
# runtime sequencers, case assertions and output writers execute as published.
g3.apply_plan = load_g3
g5.load = load_g5
paused = [case['name'] for case in g5.CONTRACT['cases'] if case.get('pause_edges')]
assert paused == ['paused-wall-clock']
g5.CONTRACT['cases'] = [case for case in g5.CONTRACT['cases'] if not case.get('pause_edges')]


class EarlyClock(DigitalPins):
    async def hand_over_clock(self):
        self.dut.clk.value = 1
        await Timer(2, unit='ns')
        self.dut.clk.value = 0
        await Timer(2, unit='ns')
        await super().hand_over_clock()


class SkippedSelector(DigitalPins):
    async def select(self, selector, rst_n):
        if self.arm_edge is not None and selector == 0x67:
            # Drop the entire command. Subsequent pin readback or the ordered
            # handoff guard must detect it even with a perfectly digital bus.
            return
        await super().select(selector, rst_n)


@cocotb.test()
async def adverse_handoffs(dut):
    directory = Path(os.environ['G3_PROGRAM_BUILD']) / 'uart_rx'
    plan = json.loads((directory / 'load-plan.json').read_bytes())
    cases = (
        ('damaged-byte', DamagedWrite(dut, 1, peer_mask=2), 'read_byte_after_edge'),
        ('peer-stuck-connected', DigitalPins(dut, peer_mask=2), 'external peer is still driving'),
        ('early-clock', EarlyClock(dut, peer_mask=2), 'unexpected clock edge'),
        ('unordered-selector', SkippedSelector(dut, peer_mask=2), 'unsafe handoff'),
    )
    observations = {}
    for name, pins, reason in cases:
        dut.uio_in.value = 2
        dut.peer_stuck.value = int(name == 'peer-stuck-connected')
        try:
            await cold_load(pins, plan)
        except TransportError as error:
            assert reason in str(error), (name, error)
            assert not pins.launched
            parked = pins.observe(('clk', 'host_mask', 'ui_in', 'rst_n', 'peer_drive', 'uio_oe'))
            assert parked == dict(clk=0, host_mask=0, ui_in=231, rst_n=0, uio_oe=0,
                                  peer_drive=2 if name == 'peer-stuck-connected' else 0), parked
            observations[name] = {'error': str(error), 'completed_rows': len(error.rows),
                                  'launched': pins.launched, 'parked': parked}
        else:
            raise AssertionError(f'{name} was accepted')
    dut.peer_stuck.value = 0
    pins = DigitalPins(dut, peer_mask=2)
    rows = await cold_load(pins, plan)
    assert pins.launched and len(rows) == 76
    observations['good-cold-retry'] = {'launched': pins.launched, 'completed_rows': len(rows)}
    (Path(os.environ['COLD_LOAD_OUT']) / 'controls.json').write_bytes(json_bytes(observations))
