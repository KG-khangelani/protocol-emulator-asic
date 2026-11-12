# SPDX-License-Identifier: Apache-2.0
"""Explicit mid-transaction controls, isolated loading, and fresh recovery."""
import heapq
import hashlib
import json
from pathlib import Path
import os
import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time
from test import initialise, edge
from test_i2c_general_public import load_and_check, VARIANT
from experiments.i2c.general_programs import image, encode
from experiments.i2c.public_bus import public_snapshot, run_bus
from experiments.i2c.target import Target
from tools.i2c_oracle import Transaction, assess, assess_abort

OUT = Path(os.environ["I2C_GENERAL_RECORD_DIR"])


def normalized(rows):
    initial = next(i for i, r in enumerate(rows) if r["oe"] == 28 and r["out"] == 0 and r["bus"] == 3)
    assert all(not r["out"] & r["oe"] & 3 for r in rows[:initial+1])
    offset = rows[initial]["t"]
    return [dict(r, t=r["t"]-offset) for r in rows[initial:]], offset


async def abort_trace(dut, target, control, release):
    """Quarter-clock digital trace; control and clock settle within one grid tick.

    The first active edge is tick four. Controls are applied before the chosen
    positive edge within that same 5 ns interval, then every actual public
    effect is sampled. This intentionally does not model analog timing.
    """
    current = await public_snapshot(dut, extended_pc=True)
    rows = [dict(current, t=0, bus=3, target_out=0, target_oe=0,
                 rst_n=1, ena=1, load=0, target_isolated=0)]
    queue, target_oe, bus = [], 0, 3
    abort_at = None
    dut.ena.value = 1
    origin = int(get_sim_time(unit="ps"))
    for tick in range(1, 100001):
        delay = origin + tick*5000 - int(get_sim_time(unit="ps"))
        assert delay > 0
        await Timer(delay, unit="ps")
        aborted = abort_at is not None and tick >= abort_at
        if tick == abort_at:
            queue.clear()
            if control == "reset":
                dut.rst_n.value = 0
            elif control == "disable":
                dut.ena.value = 0
            else:
                target_oe = 0
                dut.ui_in.value = 0xC0
                dut.uio_in.value = 0x7f
        # Settle control before this edge, without advancing the 5 ns grid.
        await Timer(1, unit="ps")
        if tick % 4 == 0:
            dut.clk.value = 1
        elif tick % 4 == 2:
            dut.clk.value = 0
        await Timer(1, unit="ps")
        before = current
        if aborted and control == "load":
            # Target is isolated. Read the actual result through loader reads,
            # keeping load_mode asserted, then restore the write selection.
            dut.ui_in.value = 0xA2
            await Timer(1, unit="ps")
            rx = int(dut.uio_out.value)
            dut.ui_in.value = 0xA3
            await Timer(1, unit="ps")
            valid = int(dut.uio_out.value)
            dut.ui_in.value = 0xC0
            await Timer(1, unit="ps")
            status = int(dut.uo_out.value)
            current = dict(out=int(dut.uio_out.value), oe=int(dut.uio_oe.value),
                           state=("RUN", "WAIT", "HALT", "FAULT")[status >> 6],
                           pc=status & 31, rx=rx, rx_valid=valid)
        else:
            current = await public_snapshot(dut, extended_pc=True)
        if not aborted:
            for event in target.controller(tick, before, current):
                heapq.heappush(queue, event)
            if abort_at is None and target.releases == release:
                assert tick % 4 == 0
                abort_at = tick+32
            while queue and queue[0][0] <= tick:
                _, mask, value = heapq.heappop(queue)
                target_oe = (target_oe & ~mask) | value
            resolved = ((current["out"] & current["oe"]) | ~current["oe"]) & ~target_oe & 3
            for event in target.bus(tick, bus, resolved):
                heapq.heappush(queue, event)
            bus = resolved
            dut.uio_in.value = bus
        elif control != "load":
            bus = ((current["out"] & current["oe"]) | ~current["oe"]) & ~target_oe & 3
            dut.uio_in.value = bus
        row = dict(current, t=tick, bus=bus, target_out=0, target_oe=target_oe,
                   rst_n=int(dut.rst_n.value), ena=int(dut.ena.value),
                   load=int(dut.ui_in.value) >> 7, target_isolated=int(aborted and control == "load"))
        if tick == abort_at or any(row[k] != rows[-1][k] for k in row if k != "t"):
            rows.append(row)
        if aborted and tick == abort_at+32:
            if rows[-1]["t"] != tick:
                rows.append(row)
            break
    assert abort_at is not None and rows[-1]["t"] >= abort_at+32
    dut.clk.value = 0
    dut.ena.value = 0
    await Timer(1, unit="ps")
    return rows, abort_at


@cocotb.test()
async def public_i2c_abort_and_reload(dut):
    OUT.mkdir(parents=True, exist_ok=True)
    for control in ("reset", "disable", "load"):
        for release in (1, 9, 19, 28, 36, 38):
            case = Transaction()
            initialise(dut)
            await edge(dut, rst_n=0, ena=0)
            program, data, _ = image(case.kind, case.address, case.tx, variant=VARIANT)
            await load_and_check(dut, [encode(w) for w in program], data)
            rows, tick = await abort_trace(dut, Target(case), control, release)
            trace, offset = normalized(rows)
            report = assess_abort(trace, case, control=control, tick=tick-offset)
            name = f"{control}-{release}"
            record = dict(name=name, control=control, release=release, variant=VARIANT,
                          errors=report["errors"], outcome=report["outcome"], abort_tick=tick-offset,
                          trace_sha256=hashlib.sha256(json.dumps(trace, sort_keys=True).encode()).hexdigest())
            (OUT/(name+".json")).write_text(json.dumps(dict(record=record, trace=trace), separators=(",", ":"))+"\n")
            with (OUT/"aborts.jsonl").open("a") as f:
                f.write(json.dumps(record, sort_keys=True)+"\n")
            assert not report["errors"], record
            # Every control is followed by a fresh public load, with no new reset.
            dut.rst_n.value = 1
            recovery = Transaction(kind="read", address=0x31, rx=0x5a)
            program, data, _ = image(recovery.kind, recovery.address, recovery.tx, variant=VARIANT)
            await load_and_check(dut, [encode(w) for w in program], data)
            fresh = await run_bus(dut, Target(recovery), bound_ticks=8000000, extended_pc=True)
            fresh, _ = normalized(fresh)
            judged = assess(fresh, recovery)
            record = dict(name="recovery-"+name, variant=VARIANT, errors=judged["errors"], outcome=judged["outcome"],
                          trace_sha256=hashlib.sha256(json.dumps(fresh, sort_keys=True).encode()).hexdigest())
            (OUT/("recovery-"+name+".json")).write_text(json.dumps(dict(record=record, trace=fresh), separators=(",", ":"))+"\n")
            with (OUT/"aborts.jsonl").open("a") as f:
                f.write(json.dumps(record, sort_keys=True)+"\n")
            assert not judged["errors"], record
