# SPDX-License-Identifier: Apache-2.0
"""Simulator entry point for one caller's artifact directory."""

import os
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'test'), str(ROOT)]
from test import edge
from test_uart_rx_public import drive_rx, host_observer, finish_host, runtime_snapshot
from tools.assembler import json_bytes
from tools.cold_load import UART_BINARY
from tools.host_transport.controller import TransportError, cold_load, read_image
from tools.host_transport.digital import DigitalPins
from tools.uart_rx_host_service import HostReader
from tools.uart_rx_oracle import Frame, expected_schedule


async def receive_uart(dut):
    dut.ui_in.value = 0x64
    await Timer(1, unit='ns')
    reader = HostReader(period=434, poll_gap=4338, read_latency=2)
    observer = host_observer(reader)
    await drive_rx(dut, [Frame(0x96), Frame(0x69)], observer=observer)
    await finish_host(dut, reader, observer, expected_schedule(period=434, start_quarter=17)['halt'])
    status, _, _ = await runtime_snapshot(dut, ())
    if reader.accepted != (0x96, 0x69) or reader.rejected or status != 0xa7:
        raise RuntimeError(f'UART delivery failed: received {reader.accepted}, terminal {status:02X}')
    return {'uart_received': list(reader.accepted), 'terminal': f'{status:02X}'}


@cocotb.test()
async def load_and_start(dut):
    output = Path(os.environ['COLD_LOAD_OUT'])
    image, plan = read_image(output / 'image')
    uart_demo = (image['binary_sha256'] == UART_BINARY and image['idle_inputs'] == 2
                 and image['payloads'] == {'TX0': 255, 'TX1': 255})
    operations = []
    pins = DigitalPins(dut, peer_mask=2 if uart_demo else 0, trace=operations)
    receipt = {'status': 'INCOMPLETE', 'operations': operations}
    rows = []
    try:
        rows = await cold_load(pins, plan)
        if uart_demo:
            receipt['runtime'] = await receive_uart(dut)
        else:
            await edge(dut)
            receipt['runtime'] = {'first_edge': pins.observe(('uo_out', 'uio_out', 'uio_oe'))}
        receipt['status'] = 'PASS'
    except Exception as error:
        if isinstance(error, TransportError):
            rows = error.rows
        receipt.update(status='FAILED', error=str(error))
        raise
    finally:
        verified = sum(row['action'] == 'read_byte_after_edge' and row['expected'] == row['actual'] for row in rows)
        receipt.update(launched=pins.launched, verified_bytes=verified, loader=rows, handoff=pins.handoff)
        (output / 'transcript.json').write_bytes(json_bytes(receipt))
