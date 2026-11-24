# SPDX-License-Identifier: Apache-2.0
"""Run a version-1 macro-port image on a continuously selected project."""

import json
from pathlib import Path
import re

from tools.assembler import json_bytes, load_plan, program_bytes


def read_image(directory: Path):
    image = json.loads((directory / 'program.json').read_bytes())
    if not re.fullmatch('[0-9a-f]{64}', str(image.get('source_sha256', ''))):
        raise ValueError('missing or invalid source digest in program.json')
    if program_bytes(image) != (directory / 'program.bin').read_bytes():
        raise ValueError('program.bin differs from the versioned image')
    plan = json.loads((directory / 'load-plan.json').read_bytes())
    if json_bytes(plan) != json_bytes(load_plan(image)):
        raise ValueError('load-plan.json differs from the image, payloads or idle inputs')
    return image, plan


class TransportError(ValueError):
    """The controller stopped with the clock parked. Rows include the first mismatch."""

    def __init__(self, message, rows=None):
        super().__init__(message)
        self.rows = rows if rows is not None else []


async def cold_load(pins, plan):
    """Return observed loader rows. The caller supplies the first runtime rising edge."""
    rows = []
    try:
        await pins.take_clock_and_isolate()
        connected = False
        for index, step in enumerate(plan['steps']):
            flush = step['action'] == 'flush_idle'
            selector = 0xE7 if flush else step['ui_in']
            await pins.release_host()
            await pins.select(selector, step['rst_n'])
            if step['host_drives_uio']:
                await pins.drive_host(step['uio_in'])
            if flush and not connected:
                await pins.connect_peer(step['uio_in'])
                connected = True
            await pins.clock_once()
            actual = pins.observe(step['expected'])
            raw = pins.host_data() if step['host_drives_uio'] else step['uio_in']
            rows.append(dict(step=index, action=step['action'], raw=raw, ui_in=selector,
                             rst_n=step['rst_n'], ena=1, host_drives_uio=step['host_drives_uio'],
                             expected=step['expected'], actual=actual))
            if actual != step['expected']:
                raise TransportError(f"step {index} {step['action']}: observed {actual}, expected {step['expected']}")

        for selector, status in ((0x67, 0x22), (0, 0x20)):
            await pins.select(selector, 1)
            if pins.observe(('uo_out', 'uio_oe')) != {'uo_out': status, 'uio_oe': 0}:
                raise TransportError(f'unsafe handoff at selector {selector:02x}')
        await pins.hand_over_clock()
    except Exception as error:
        await pins.abort()
        if isinstance(error, TransportError):
            error.rows = rows
        raise
    return rows
