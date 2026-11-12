# SPDX-License-Identifier: Apache-2.0
"""Complete transactions on isolated general-ISA candidates, public pins only."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import cocotb
from cocotb.triggers import Timer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, write_data_register, settle_program_read, G2_SRAM
from experiments.i2c.general_programs import image, encode
from experiments.i2c.public_bus import run_bus
from experiments.i2c.target import Target
from tools.i2c_oracle import Transaction, assess

VARIANT = os.environ["I2C_GENERAL_VARIANT"]
OUT = Path(os.environ["I2C_GENERAL_RECORD_DIR"])
SMOKE = os.getenv("I2C_GENERAL_SMOKE") == "1"


async def load_and_check(dut, words, data):
    capacity = 128 if VARIANT == "od128" else 255
    assert len(words) <= capacity
    bank = 0
    for n, word in enumerate(words):
        if n//8 != bank:
            bank = n//8
            await write_data_register(dut, 5, bank)
        for lane in range(4):
            dut.ui_in.value = 0xC0 | (n%8)*4 | lane
            dut.uio_in.value = word >> (8*lane) & 255
            await edge(dut)
            assert int(dut.uio_oe.value) == 0
    await write_data_register(dut, 0, len(words))
    bank = 0
    for n, word in enumerate(words):
        if n//8 != bank:
            bank = n//8
            await write_data_register(dut, 5, bank)
        for lane in range(4):
            dut.ui_in.value = 0x80 | (n%8)*4 | lane
            await settle_program_read(dut)
            assert int(dut.uio_out.value) == word >> (8*lane) & 255
            assert int(dut.uio_oe.value) == 255
    await write_data_register(dut, 0, len(words))
    for register, value in data.items():
        await write_data_register(dut, register, value)
    dut.ui_in.value = 0xA7
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == (0x22 if G2_SRAM else 0x21 if VARIANT == "od128" else 0x20)
    dut.ui_in.value = 0
    dut.uio_in.value = 3
    await edge(dut, ena=0)
    await edge(dut, ena=0)


async def transaction(dut, name, case, *, response=4, stretches=None, mutate=None, expected=True, glitch_release=None):
    program, data, labels = image(case.kind, case.address, case.tx, variant=VARIANT)
    if mutate:
        program, data = mutate(program, data)
    words = [encode(w) for w in program]
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_and_check(dut, words, data)
    target = Target(case, response=response, stretches=stretches, glitch_release=glitch_release)
    rows = await run_bus(dut, target, bound_ticks=8000000, extended_pc=True)
    # Initialization is checked separately; the contract starts once the first
    # SET establishes markers and released bus. Preserve its full idle interval.
    initial = next((i for i, r in enumerate(rows) if r["oe"] == 28 and r["out"] == 0 and r["bus"] == 3), None)
    initialization_errors = []
    if initial is None:
        initial = 0
        initialization_errors.append({"kind": "initialization", "t": 0})
    for row in rows[:initial+1]:
        if row["out"] & row["oe"] & 3:
            initialization_errors.append({"kind": "initialization_active_high", "t": row["t"]})
    offset = rows[initial]["t"]
    trace = [dict(r, t=r["t"]-offset) for r in rows[initial:]]
    report = assess(trace, case)
    errors = initialization_errors+report["errors"]
    record = {"name": name, "scope": "ISOLATED_GENERAL_CANDIDATE_PUBLIC_I2C_RTL",
              "variant": VARIANT, "kind": case.kind, "address": case.address, "tx": case.tx, "rx": case.rx,
              "nack": case.nack, "timeout_release": case.timeout_release, "response": response,
              "stretches": stretches or {}, "words": len(words), "labels": labels,
              "expected_acceptance": expected, "accepted": not errors,
              "errors": sorted({e["kind"] for e in errors}), "first_errors": errors[:8],
              "outcome": report["outcome"], "fastest_hz": report["fastest_hz"],
              "trace_sha256": hashlib.sha256((json.dumps(trace, sort_keys=True, separators=(",", ":"))+"\n").encode()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/"cases.jsonl").open("a") as f:
        f.write(json.dumps(record, sort_keys=True)+"\n")
    if SMOKE or errors or case.tx in (0, 0x96, 255) or case.nack or case.timeout_release:
        (OUT/(name+".json")).write_text(json.dumps({"record": record, "words": [f"{w:08x}" for w in words],
                                                  "data": data, "trace": trace, "target": target.decoded},
                                                 separators=(",", ":"))+"\n")
    assert (not errors) == expected, record


@cocotb.test()
async def complete_i2c_transactions(dut):
    for kind in ("write", "read", "write_read"):
        values = (0x96,) if SMOKE else range(256)
        for byte in values:
            await transaction(dut, f"{kind}-{byte:02x}", Transaction(kind=kind, address=8+byte%112,
                              tx=byte, rx=(37*byte+83)%256), response=(4, 5, 690, 7)[byte%4])
    for kind, nack in (("write", "address"), ("write", "data"), ("read", "address"),
                       ("write_read", "address"), ("write_read", "data"), ("write_read", "read_address")):
        await transaction(dut, f"{kind}-nack-{nack}", Transaction(kind=kind, nack=nack))
    for kind, releases in (("write", 19), ("read", 19), ("write_read", 38)):
        if SMOKE and kind != "write_read":
            continue
        for release in ((1, 9, 18, 19, 20, 28, 36, 37, 38) if SMOKE else range(1, releases+1)):
            await transaction(dut, f"{kind}-stretch-{release}", Transaction(kind=kind), response=690, stretches={release: 1001})
        for delay, label in ((199987, "before"), (199991, "final"), (199992, "late"), (None, "permanent")):
            for release in ((4, 38) if SMOKE else range(1, releases+1)):
                case = Transaction(kind=kind, timeout_release=release if delay in (199992, None) else None)
                await transaction(dut, f"{kind}-deadline-{label}-{release}", case, stretches={release: delay})

    def active_high(program, data):
        program = list(program)
        index = next(i for i, w in enumerate(program) if i >= 5 and
                     (w.opcode == "DRIVE" if VARIANT == "od128" else w.opcode == "SET" and w.mask == 2))
        w = program[index]
        program[index] = replace(w, open_drain=False) if VARIANT == "od128" else replace(w, oe=2, value=2)
        return program, data

    def wrong_address(program, data):
        if VARIANT == "od128":
            data = dict(data)
            data[1] ^= 2
        else:
            program = list(program)
            program[5] = replace(program[5], oe=program[5].oe ^ 2)
        return program, data

    def wrong_order(program, data):
        return [replace(w, msb_first=0) if w.opcode == "SHIFT_STEP" else w for w in program], data

    def hold_sda(program, data):
        return [replace(w, oe=30) if w.opcode == "SET" and w.value == 12 else w for w in program], data

    def late_wait(program, data):
        return [replace(w, count=50000) if w.opcode == "WAIT_PIN" and w.pin == 0 else w for w in program], data

    for name, mutation in (("active-high", active_high), ("wrong-address", wrong_address), ("wrong-order", wrong_order)):
        await transaction(dut, "negative-"+name, Transaction(), mutate=mutation, expected=False)
    await transaction(dut, "negative-cleanup-holds-sda", Transaction(timeout_release=4),
                      mutate=hold_sda, stretches={4: None}, expected=False)
    await transaction(dut, "negative-late-input-accepted", Transaction(timeout_release=4),
                      mutate=late_wait, stretches={4: 199992}, expected=False)
    await transaction(dut, "negative-sda-high-glitch", Transaction(), glitch_release=1, expected=False)
