# SPDX-License-Identifier: Apache-2.0
"""Measure both physical SCL input traces relative to the FPGA's sampled output-enable command."""
import argparse
from bisect import bisect_right
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from experiments.remote_i2c.check import IMAGES, REQUESTS, need, stable_bus, wire_result

LINK, SDA, TARGET, SDA_OE, HALT, SCL_OE = (1 << n for n in (0, 7, 8, 10, 11, 15))
MASK = LINK | SDA | TARGET | SDA_OE | HALT | SCL_OE


def edges(values, mask):
    return [t for t in range(1, len(values)) if (values[t] ^ values[t - 1]) & mask]


def extent(observations):
    return {"n": len(observations), "min": min(observations, default=None), "max": max(observations, default=None)}


def expand(changes, count):
    need(changes and changes[0][0] == 0, "first sample")
    values = []
    for (start, level), (end, nxt) in zip(changes, changes[1:] + [[count, None]]):
        need(start < end <= count and level != nxt and not level & ~MASK, "raw sample journal")
        values.extend([level] * (end - start))
    return values


def decode_wire(changes, count, scl, reg, reply, positive, period):
    bus = []
    for t, v in changes:
        level = (2 * bool(v & SDA) + 4 * bool(v & scl) + 16 * bool(v & SDA_OE) + 32 * bool(v & HALT))
        if not bus or bus[-1][1] != level:
            bus.append([t, level])
    scores = {}
    for name, pins in (("raw", bus), ("five_samples", stable_bus(bus, count, 5))):
        result = wire_result(pins, count, positive, reg, reply)
        if result["passed"]:
            b = result["boundaries"]
            result["start_to_stop_ns"] = (b[-1][1] - b[0][1]) * period
        scores[name] = result
    return scores


def input_timing(values, observed, commands, period):
    transitions = edges(values, observed)
    short_runs = Counter()
    widths = Counter()
    first_delay = {0: [], 1: []}
    stable_delay = {0: [], 1: []}
    missing = Counter()
    for start, end in zip(transitions, transitions[1:]):
        width = (end - start) * period
        if width >= 500:
            continue
        crosses = any((values[t] ^ values[start]) & SCL_OE for t in range(start, end + 1))
        command = "crosses" if crosses else "asserted" if values[start] & SCL_OE else "released"
        level = "high" if values[start] & observed else "low"
        short_runs[command + "_" + level] += 1
        widths[width] += 1
    first_low = {}
    for start, end in zip(commands, commands[1:] + [len(values)]):
        asserted = int(bool(values[start] & SCL_OE))
        expected = not asserted
        first = next((t for t in range(start, end) if bool(values[t] & observed) == expected), None)
        if first is None:
            missing["assert" if asserted else "release"] += 1
            continue
        if asserted:
            first_low[start] = first
        first_delay[asserted].append((first - start) * period)
        if bool(values[end - 1] & observed) == expected:
            last_wrong = next((t for t in range(end - 2, start - 1, -1) if bool(values[t] & observed) != expected),
                              start - 1)
            stable_delay[asserted].append((last_wrong + 1 - start) * period)
    sda_after_sampled_fall = []
    sda_after_command = []
    for t in edges(values, SDA_OE):
        if values[t] & SCL_OE:
            i = bisect_right(commands, t) - 1
            if i >= 0 and commands[i] in first_low:
                start = commands[i]
                sda_after_sampled_fall.append((t - first_low[start]) * period)
                sda_after_command.append((t - start) * period)
    return dict(edges=len(transitions), short_counts=dict(sorted(short_runs.items())), short_widths_ns=dict(widths),
                first_low_after_assert_ns=extent(first_delay[1]), first_high_after_release_ns=extent(first_delay[0]),
                sustained_low_after_assert_ns=extent(stable_delay[1]), sustained_high_after_release_ns=extent(stable_delay[0]),
                phases_without_expected_level=dict(missing), sda_command_after_first_sampled_low_ns=extent(sda_after_sampled_fall),
                sda_command_after_scl_command_ns=extent(sda_after_command))


def analyze(changes, count, reg, reply, positive, period):
    values = expand(changes, count)
    commands = edges(values, SCL_OE)
    expected_edges = 76 if positive else 20
    result = dict(scl_command_edges=len(commands), expected_command_edges=expected_edges,
                  commands_match=len(commands) == expected_edges and not (values[0] | values[-1]) & SCL_OE,
                  samples=count, period_ns=period)
    for where, mask in (("target_gpio27", TARGET), ("linked_gpio19", LINK)):
        result[where] = {**input_timing(values, mask, commands, period),
                         **decode_wire(changes, count, mask, reg, reply, positive, period)}
    disagreements = Counter()
    runs = []
    width = 0
    for v in values:
        if bool(v & TARGET) != bool(v & LINK):
            disagreements["only_target_high" if v & TARGET else "only_link_high"] += 1
            width += 1
        elif width:
            runs.append(width * period)
            width = 0
    if width:
        runs.append(width * period)
    result["input_disagreement_samples"] = dict(disagreements)
    result["input_disagreement_run_ns"] = extent(runs)
    return result


def score(path):
    raw = gzip.decompress(path.read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "complete terminal")
    stdout, stderr = raw[2:-2].split(b"\x04", 1)
    need(not stderr, "board exception")
    records = [json.loads(line[7:]) for line in stdout.splitlines() if line.startswith(b"I2CLAB ")]
    start, finish = records[0], records[-1]
    hz = start["sample_hz"]
    need(start["event"] == "start" and hz in (8_000_000, 10_000_000) and start["system_hz"] == 125_000_000
         and (start["project_divisor"], start["gpio_base"], start["in_base"], start["pin_mask"]) == (10, 16, 19, MASK),
         "capture clock and pin mapping")
    need(finish["event"] == "finish" and finish["restored_bank"] == start["initial_bank"]
         and finish["restored_hz"] == start["original_hz"] and finish["host_uio_oe"] == 0, "fixture cleanup")
    wanted = {f"{guard}-{reg:02x}-{addr:02x}": (guard, reg, reply, addr)
              for guard in IMAGES for reg, reply, addr in REQUESTS}
    pins, cases = {}, {}
    for record in records[1:-1]:
        name = record["name"]
        guard, reg, reply, addr = wanted[name]
        if record["event"] == "cold":
            image = bytes.fromhex(record["image"])
            need(name not in pins and (len(image), hashlib.sha256(image).hexdigest()) == IMAGES[guard]
                 and record["rows"] == (802 if guard == 0 else 902)
                 and record["registers"] == [[0xa0, len(image) // 4], [0xa1, 0x5c], [0xa4, reg]], "cold image " + name)
            pins[name] = []
        elif record["event"] == "pins":
            need(name in pins and name not in cases and record["changes"], "pin fragment " + name)
            pins[name].extend(record["changes"])
        else:
            need(record["event"] == "trace" and name in pins and name not in cases, "trace " + name)
            positive = addr == 0x2e
            need([record[k] for k in ("target_address", "register", "reply", "sample_hz", "samples")]
                 == [addr, reg, reply, hz, hz * 24 // 10000] and record["idle"][:3] == [1, 1, 1], "stimulus " + name)
            need((record["status"], record["rx"], record["valid"]) == ((0x88, reply, 1) if positive else (0x90, 0, 1)),
                 "peripheral outcome " + name)
            cases[name] = analyze(pins[name], record["samples"], reg, reply, positive, 1_000_000_000 // hz)
            cases[name].update(status=record["status"], read_byte=record["rx"], offset=reg, address=addr)
    need(set(cases) == set(pins) == set(wanted), "all six trials are complete")
    return {"start": start, "finish": finish, "cases": cases}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("terminal", type=Path)
    p.add_argument("--require-clean", action="store_true")
    args = p.parse_args()
    decoded = score(args.terminal)
    print(json.dumps(decoded, indent=2, sort_keys=True))
    if args.require_clean and not all(c["commands_match"] and c["target_gpio27"]["raw"]["passed"]
                                      and c["linked_gpio19"]["raw"]["passed"] for c in decoded["cases"].values()):
        raise SystemExit(1)
