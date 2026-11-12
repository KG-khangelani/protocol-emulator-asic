# SPDX-License-Identifier: Apache-2.0
"""Reuse the existing shifter's zero TX bit as SCL's falling capture edge."""
import sys
from pathlib import Path
import cocotb
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, write_data_register, encode
from test_i2c_baseline_public import load_and_check, save
from tools.m1_contract_model import Instruction as I
from experiments.i2c.public_bus import run_bus


class ByteTarget:
    """Respond only to public SCL events; no instruction/PC knowledge."""
    def __init__(self, value, response, stretches):
        self.value, self.response, self.stretches = value, response, stretches
        self.rises = 0
        self.releases = 0

    def controller(self, tick, before, after):
        events = []
        if before["oe"] & 1 and not after["oe"] & 1:
            self.releases += 1
            delay = self.stretches.get(self.releases, 0)
            if delay:
                events.append((tick+delay, 1, 0))
        return events

    def bus(self, tick, before, after):
        if not before & 1 and after & 1:
            self.rises += 1
        if before & 1 and not after & 1:
            value = 0 if self.rises >= 8 else 2*(1-((self.value >> (7-self.rises)) & 1))
            events = [(tick+self.response, 2, value)]
            if self.stretches.get(self.releases+1, 0) != 0 and self.rises < 8:
                events.append((tick+1, 1, 1))
            return events
        return []


def judge(rows, value):
    errors = set()
    rises, captures, lows, highs = [], [], [], []
    low = None
    high = None
    for i, row in enumerate(rows):
        if row["out"] & row["oe"] & 3:
            errors.add("active_high")
        if row["oe"] & 2:
            errors.add("controller_drives_sda")
        if not i:
            if row["rx_valid"]:
                errors.add("old_valid")
            continue
        prior = rows[i-1]
        if prior["bus"] & 1 and not row["bus"] & 1:
            low = row["t"]
            if high is not None:
                highs.append(low-high)
                captures.append(low)
                high = None
        if not prior["bus"] & 1 and row["bus"] & 1:
            high = row["t"]
            if low is not None:
                lows.append(high-low)
            rises.append((high, (row["bus"] >> 1) & 1))
    if len(rises) != 8 or len(captures) != 8:
        errors.add("clock_count")
    wire_byte = sum(bit << (7-n) for n, (_, bit) in enumerate(rises[:8]))
    if wire_byte != value:
        errors.add("wire_byte")
    if any(t < 940 for t in lows) or any(t < 800 for t in highs):
        errors.add("clock_width")
    periods = [b[0]-a[0] for a, b in zip(rises, rises[1:])]
    if any(t < 2000 for t in periods):
        errors.add("clock_frequency")
    commit = captures[-1] if len(captures) == 8 else None
    for row in rows:
        ready = commit is not None and row["t"] >= commit
        if row["rx_valid"] != int(ready) or row["rx"] != (value if ready else rows[0]["rx"]):
            errors.add("raw_capture")
    if rows[-1]["state"] != "HALT":
        errors.add("terminal")
    return {"errors": sorted(errors), "wire_byte": wire_byte, "rises": rises,
            "captures": captures, "low_ticks": lows, "high_ticks": highs,
            "fastest_hz": 200000000/min(periods) if periods else None}


async def transfer(dut, name, value, *, response=4, stretches=None, tx=0, order=1, high=240, expected=True, reset=False):
    if reset:
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
    program = [I("SET", mask=31, oe=28), I("SET", mask=1, oe=1), I("LOOP", length=5, count=8),
               I("WAIT", count=260), I("SET", mask=1),
               I("WAIT_PIN", pin=0, level=1, count=49999, timeout_skip=1),
               I("WAIT", count=high), I("SHIFT_STEP", tx_pin=0, rx_pin=1, msb_first=order), I("HALT")]
    words = [encode(w) for w in program]
    await load_and_check(dut, words)
    await write_data_register(dut, 1, tx)
    dut.ui_in.value = 0
    dut.uio_in.value = 3
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    rows = await run_bus(dut, ByteTarget(value, response, stretches or {}), bound_ticks=300000)
    result = judge(rows, value)
    record = {"scope": "EXISTING_SHIFT_RECEIVE_KERNEL_NOT_I2C_TRANSACTION", "value": value,
              "target_response_ticks": response, "stretches": stretches or {},
              "words": [f"{w:08x}" for w in words], "word_count": len(words),
              "expected_acceptance": expected, "accepted": not result["errors"],
              "terminal_state": rows[-1]["state"], "result": result}
    save(name, record, rows if not expected or value in (0, 0x69, 255) else None)
    assert (not result["errors"]) == expected, record


@cocotb.test()
async def same_pin_clock_capture_with_public_reload(dut):
    for value in range(256):
        await transfer(dut, f"byte-{value:02x}", value,
                       response=(4, 5, 690, 7)[value % 4], reset=value == 0)
    for release in range(1, 9):
        await transfer(dut, f"stretch-{release}", 0x69, response=690, stretches={release: 503+release%4})
    await transfer(dut, "wrong-tx-active-high", 0x69, tx=0x80, expected=False)
    await transfer(dut, "wrong-bit-order", 0x69, order=0, expected=False)
    await transfer(dut, "wrong-high-delay", 0x69, high=0, expected=False)
    await transfer(dut, "timeout-mid-byte", 0x69, stretches={4: None}, expected=False)
