# SPDX-License-Identifier: Apache-2.0
"""Actual compact10 public loading and existing-instruction boundary kernels."""
import hashlib
import json
import os
from pathlib import Path
import sys
import cocotb
from cocotb.triggers import Timer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, write_data_register
from experiments.i2c.baseline_programs import encode, wait_kernel, write_wire_baseline

OUT = Path(os.environ["I2C_BASELINE_RECORD_DIR"])


async def load_and_check(dut, words):
    assert len(words) <= 10
    bank = 0
    for index, word in enumerate(words):
        if index//8 != bank:
            bank = index//8
            await write_data_register(dut, 5, bank)
        for lane in range(4):
            dut.ui_in.value = 0xC0 | (index%8)*4 | lane
            dut.uio_in.value = word >> (8*lane) & 255
            await edge(dut)
            assert int(dut.uio_oe.value) == 0
    await write_data_register(dut, 0, len(words))
    bank = 0
    for index, word in enumerate(words):
        if index//8 != bank:
            bank = index//8
            await write_data_register(dut, 5, bank)
        for lane in range(4):
            dut.ui_in.value = 0x80 | (index%8)*4 | lane
            await Timer(1, unit="ns")
            assert int(dut.uio_oe.value) == 255
            assert int(dut.uio_out.value) == word >> (8*lane) & 255
    await write_data_register(dut, 0, len(words))
    assert int(dut.uo_out.value) & 32


def save(name, record, rows=None):
    OUT.mkdir(parents=True, exist_ok=True)
    if rows is not None:
        blob = (json.dumps(rows, sort_keys=True, separators=(",", ":"))+"\n").encode()
        (OUT/(name+".json")).write_bytes(blob)
        record["trace_sha256"] = hashlib.sha256(blob).hexdigest()
    with (OUT/"cases.jsonl").open("a") as f:
        f.write(json.dumps(dict(name=name, **record), sort_keys=True)+"\n")


async def kernel(dut, name, delay, *, loop=False, skip=True):
    program = wait_kernel(loop=loop, skip=skip)
    words = [encode(w) for w in program]
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_and_check(dut, words)
    await write_data_register(dut, 1, 0)  # Public raw-valid invalidation.
    dut.ui_in.value = 0
    dut.uio_in.value = 3
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    dut.ena.value = 1
    target_oe = 0
    release = None
    raw_high = None
    last_oe = 0
    held = False
    terminal = None
    rows = []
    # Quarter-clock driver preserves post-edge target offsets and pin feedback.
    t = 4
    while t < 4*50540:
        if t % 4 == 0:
            dut.clk.value = 1
        elif t % 4 == 2:
            dut.clk.value = 0
        await Timer(1, unit="ps")
        if t % 4 == 0:
            out, oe = int(dut.uio_out.value), int(dut.uio_oe.value)
            status = int(dut.uo_out.value)
        if oe & 1 and not held:
            held = True
            target_oe = int(delay != 0)
        if last_oe & 1 and not oe & 1 and release is None:
            release = t
        if release is not None and delay is not None and t >= release+delay:
            target_oe = 0
        bus = 3 & ~(oe | target_oe)
        dut.uio_in.value = bus
        if release is not None and bus & 1 and raw_high is None:
            raw_high = t
        state = ("RUN", "WAIT", "HALT", "FAULT")[status >> 6]
        row = {"t": t, "out": out, "oe": oe, "target_oe": target_oe,
               "bus": bus, "state": state, "pc": status & 31}
        if not rows or any(row[k] != rows[-1][k] for k in row if k != "t"):
            rows.append(row)
        assert not out & oe & 3, row
        last_oe = oe
        if state in ("HALT", "FAULT") and terminal is None:
            terminal = row
        if terminal and t >= terminal["t"]+16:
            rows.append(row)
            break
        next_tick = (t//2+1)*2
        if release is not None and delay is not None and t < release+delay < next_tick:
            next_tick = release+delay
        await Timer((next_tick-t)*5000-1, unit="ps")
        t = next_tick
    assert release is not None and terminal is not None, name
    d = release+200000
    # Independent arithmetic from the frozen public synchronizer contract.
    seen = None if raw_high is None else (raw_high//4+3)*4
    timeout = seen is None or seen > d
    wanted_fault = timeout and (loop or not skip)
    if wanted_fault:
        assert terminal["state"] == "FAULT" and terminal["t"] == d, (name, terminal, d)
        assert terminal["oe"] & 3 == 2 and terminal["out"] & 28 == 0
    elif timeout:
        assert terminal["state"] == "HALT" and terminal["t"] == d+8, (name, terminal, d)
        assert terminal["oe"] == 28 and terminal["out"] == 12
    else:
        expected = seen + (8 if loop else 12)
        assert terminal["state"] == "HALT" and terminal["t"] == expected, (name, terminal, expected)
        assert terminal["oe"] == 28 and terminal["out"] == 4
    save(name, {"scope": "ACTUAL_PUBLIC_LOADED_KERNEL_NOT_I2C_TRANSACTION",
                "words": [f"{w:08x}" for w in words], "word_count": len(words),
                "delay_ticks": delay, "release_tick": release, "raw_high_tick": raw_high,
                "observed_tick": seen, "deadline_tick": d, "terminal": terminal,
                "timeout": timeout, "protocol_cleanup_pass": timeout and not wanted_fault,
                "expected_fault_holding_sda": wanted_fault}, rows)


@cocotb.test()
async def existing_wait_cleanup_and_final_observation_edge(dut):
    for name, delay in (("unstretched", 0), ("short-stretch", 5),
                        ("before-deadline", 199987), ("final-edge", 199991),
                        ("after-deadline", 199992), ("permanent-low", None)):
        await kernel(dut, name, delay)
    await kernel(dut, "loop-event", 5, loop=True)
    await kernel(dut, "loop-timeout-holds-sda", None, loop=True)
    await kernel(dut, "plain-timeout-holds-sda", None, skip=False)


@cocotb.test()
async def oversized_literal_transaction_is_not_public_capacity(dut):
    program = write_wire_baseline(0x52, 0x96)
    assert len(program) == 122
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    # Demonstrate the first illegal length, not a wrapped 122-word write.
    await load_and_check(dut, [encode(w) for w in wait_kernel()])
    await write_data_register(dut, 0, 11)
    assert not int(dut.uo_out.value) & 32
    dut.ui_in.value = 0
    dut.uio_in.value = 3
    for _ in range(4):
        await edge(dut)
        assert not int(dut.uo_out.value) & 32
        assert int(dut.uio_oe.value) == 0
    save("capacity", {"scope": "LITERAL_WIRE_SCHEDULE_COUNT_AND_REAL_LOADER_REJECTION",
                      "schedule_words": len(program), "schedule_bits": 32*len(program),
                      "physical_store_words": 10, "physical_store_bits": 320,
                      "pc_addressable_words": 32, "first_rejected_length": 11,
                      "word_image": [f"{encode(w):08x}" for w in program],
                      "limits": ["Not a global ISA minimum", "Oversized image not executed",
                                 "Literal success-wire schedule lacks ACK branching, receive and timeout cleanup"]})
