# SPDX-License-Identifier: Apache-2.0
"""Measure digital MISO level settling under bias on two inputs of the physical requester."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.remote_spi.branch_bias.run import BIAS, schedules
from experiments.remote_spi.check import assess, need, records, transitions
from experiments.remote_spi.remote import PROGRAM_SHA
from experiments.remote_spi.schedules import tick
from experiments.spi_target.requester import REPLIES

NS = 8
NATIVE, LINKED, ENABLE = 8, 128, 16


def decoded(row, fragments):
    count = row["count"]
    need(10 < count < 65536 and count % 4 == 0, "physical sample count")
    if row["packed"]:
        need(not fragments and 0 <= row["template"] < 1024, "packed sample clock")
        data = bytes.fromhex(row["data"])
        need(len(data) >= 3 and len(data) % 3 == 0 and data[:2] == bytes(2), "packed initial sample")
        values = bytearray(count)
        begin, level = 0, data[2]
        for i in range(3, len(data), 3):
            tick_index = data[i] | data[i+1] << 8
            need(begin < tick_index < count and level != data[i+2], "eight-input change journal")
            values[begin:tick_index] = bytes([level]) * (tick_index-begin)
            begin, level = tick_index, data[i+2]
        values[begin:] = bytes([level]) * (count-begin)
        for phase in range(10):
            if row["template"] & (1 << phase):
                values[phase::10] = bytes(v ^ 64 for v in values[phase::10])
        return values
    joined = bytearray()
    for fragment in fragments:
        need(fragment["name"] == row["name"] and fragment["bias"] == row["bias"] and
             fragment["offset"] == len(joined), "raw sample fragment")
        joined.extend(bytes.fromhex(fragment["data"]))
    need(len(joined) == row["count"]*2, "complete raw sample array")
    result = bytearray()
    for i in range(0, len(joined), 2):
        raw = joined[i] | joined[i+1] << 8
        result.append(((raw >> 5) & 127) | ((raw & 1) << 7))
    return result


def pin_observation(raw, pin, drive, bias, origin, off, end, select):
    def level(t):
        return int(bool(raw[t] & pin))
    goal = None if bias == 0 else int(bias > 0)
    after = [level(t) for t in range(off, end)]
    edges = sum(a != b for a, b in zip([level(off-1)] + after, after))
    first = stable = None
    if goal is not None and goal in after:
        first = after.index(goal)
        if after[-1] == goal:
            wrong = next((i for i in reversed(range(len(after))) if after[i] != goal), -1)
            stable = wrong + 1
    return dict(prior=level(origin-1), last_driven=level(off-1), preoff_expected=drive,
                at_oe_fall=after[0], at_fresh_select=None if select is None else level(select),
                end=after[-1], receiver_edges=edges, first_bias_after_oe_ns=None if first is None else NS*first,
                sustained_bias_after_oe_ns=None if stable is None else NS*stable,
                sustained_before_select_lower_ns=None if stable is None or select is None else NS*(select-off-stable-1))


def check_pads(row):
    bias = tuple(row["bias"])
    need(bias in BIAS and len(row["pads"]) == 2, "known receiver bias")
    for (gpio, pad, control, status), expected_gpio, meaning in zip(row["pads"], (20, 28), bias):
        need(gpio == expected_gpio and (pad & 12) == {-1:4, 0:0, 1:8}[meaning]
             and (pad & ~12) == 0x52 and control == 5 and not (status & 0x2000),
             "physical input function, bias and disabled driver")
    return bias


def trial(row, raw, desc, case):
    bias = check_pads(row)
    checks = {}
    for label, pin in (("gp28", NATIVE), ("gp20", LINKED)):
        view = bytes(((v & 0x77) | (8 if v & pin else 0)) for v in raw)
        checks[label] = assess(desc, dict(row, packed=False, data=view.hex()))
    cs = transitions(raw, 2)
    first = case["frames"][0]
    fresh = None
    if desc[4] == "pause":
        expected = tick(first["lost_clock"]) + cs[0] - tick(first["select"])
        origin = min(transitions(raw, 0), key=lambda t: abs(t-expected))
        need(abs(origin-expected) <= 2, "stalled clock origin")
    else:
        origin = cs[1]
        if len(case["frames"]) == 2:
            fresh = cs[2]
    need(raw[origin] & ENABLE, "active driver at abort or stall")
    enables = transitions(raw, 4)
    off = next(t for t in enables if t >= origin and not raw[t] & ENABLE)
    # Exclude the immediately adjacent bins when the FPGA starts the fresh reply.
    end = next((t-2 for t in enables if t > off), len(raw))
    need(off < end and (fresh is None or origin < fresh < end), "released observation window")
    expected_bit = (REPLIES[first["command"]] >> (7 - desc[5])) & 1
    bias_value = bias[1]
    prior_window = raw[max(0, off-4):off]
    need(len(prior_window) == 4 and all(v & ENABLE for v in prior_window), "four driven reference samples")
    for label, pin in (("gp28", NATIVE), ("gp20", LINKED)):
        obs = pin_observation(raw, pin, expected_bit, bias_value, origin, off, end, fresh)
        obs["four_driven_samples_correct"] = all(bool(v & pin) == bool(expected_bit) for v in prior_window)
        obs["idle_levels"] = sorted({int(bool(v & pin)) for v in raw[:cs[0]]})
        checks[label]["bias_observation"] = obs
    relation = "none" if bias_value == 0 else "matching" if expected_bit == int(bias_value > 0) else "opposed"
    return dict(name=row["name"], bias=list(bias), relation=relation, commanded_bit=expected_bit,
                origin_to_oe_ns=(off-origin)*NS, observed_release_window_ns=(end-off)*NS,
                origin_to_fresh_ns=None if fresh is None else (fresh-origin)*NS,
                released_pair_disagreements=sum(bool(v & NATIVE) != bool(v & LINKED) for v in raw[off:end]),
                sample_count=len(raw), receivers=checks)


def session(path, orders):
    log = records(gzip.decompress(path.read_bytes()))
    start, bad, cold = log[:3]
    need(start["event"] == "start" and start["order"] in orders and
         (start["samples_hz"], start["system_hz"], start["core_divisor"]) == (125000000,125000000,10),
         "physical sample and core clocks")
    need(bad["event"] == "readback_error" and bad["selector"] == 0x81 and bad["observed"] == (bad["expected"] ^ 1),
         "deliberate wrong-byte detection")
    image = bytes.fromhex(cold["image"])
    need(cold["event"] == "cold" and len(image) == 504 and hashlib.sha256(image).hexdigest() == PROGRAM_SHA
         and cold["rows"] == 1050 and cold["registers"] == [[160,126],[161,60],[164,167]], "full verified load")
    finish = log[-1]
    need(finish["event"] == "finish" and finish["host_uio_oe"] == 0 and
         finish["restored_hz"] == start["original_hz"], "board cleanup")
    return start, log[3:-1]


def score(path):
    start, rows = session(path, ("forward", "reverse"))
    plans = schedules()
    names, biases = list(plans), list(BIAS)
    if start["order"] == "reverse":
        names.reverse()
        biases.reverse()
    expected = [(name, bias) for bias in biases for name in names]
    cases, fragments = [], []
    for row in rows:
        if row["event"] == "raw":
            fragments.append(row)
            continue
        need(row["event"] == "trace" and len(cases) < len(expected) and
             (row["name"], tuple(row["bias"])) == expected[len(cases)], "case order and bias")
        raw = decoded(row, fragments)
        fragments.clear()
        cases.append(trial(row, raw, *plans[row["name"]]))
    need(len(cases) == len(expected) and not fragments, "complete 50-trial campaign")
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terminal", type=Path)
    args = parser.parse_args()
    print(json.dumps(score(args.terminal), indent=2))
