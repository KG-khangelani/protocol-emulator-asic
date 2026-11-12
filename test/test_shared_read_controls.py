# SPDX-License-Identifier: Apache-2.0
"""Collect public observations for D39 and three deliberate read-path faults."""
import json
import os
from pathlib import Path
import random

import cocotb
from cocotb.triggers import Timer
from test import edge, initialise, write_data_register

SEED = 20261112


@cocotb.test()
async def public_shared_read_witness(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    rng = random.Random(SEED)
    words = [rng.getrandbits(32) for _ in range(128)]
    # Raw, independent ISA fixture: SET all A5, SET all 5A, HALT.
    words[:3] = [0x00FFFFA5, 0x00FFFF5A, 0x80000000]
    writes, reads, trace = [], [], []
    for index, word in enumerate(words):
        if index % 8 == 0:
            await write_data_register(dut, 5, index // 8)
        for lane in range(4):
            address, value = 0xC0 | (index % 8) * 4 | lane, (word >> (8 * lane)) & 255
            dut.ui_in.value, dut.uio_in.value = address, value
            await edge(dut)
            assert int(dut.uio_oe.value) == 0
            writes.append([index, lane, address, value])
    for index in range(128):
        if index % 8 == 0:
            await write_data_register(dut, 5, index // 8)
        for lane in range(4):
            dut.ui_in.value = 0x80 | (index % 8) * 4 | lane
            await Timer(1, unit="ns")
            reads.append([index, lane, int(dut.uio_out.value), int(dut.uio_oe.value)])
    await write_data_register(dut, 0, 128)
    dut.ui_in.value = 0xA0
    await Timer(1, unit="ns")
    length = [int(dut.uio_out.value), int(dut.uio_oe.value)]
    ready = bool(int(dut.uo_out.value) & 32)
    dut.ui_in.value, dut.uio_in.value = 0, 0
    for _ in range(6):
        await edge(dut)
        status = int(dut.uo_out.value)
        dut.ui_in.value = 0x66
        await Timer(1, unit="ns")
        pc = int(dut.uo_out.value)
        dut.ui_in.value = 0
        await Timer(1, unit="ns")
        trace.append([pc, status >> 6, int(dut.uio_out.value), int(dut.uio_oe.value)])
    record = {"seed": SEED, "words": words, "writes": writes, "reads": reads,
              "length": length, "ready": ready, "trace": trace}
    out = Path(os.environ["SHARED_READ_RECORD"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
