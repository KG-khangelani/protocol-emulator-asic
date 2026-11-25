# SPDX-License-Identifier: Apache-2.0
"""Decode the physical 1-Wire exchange from DQ and compare to the peer FIFO and controller pins."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import need
from experiments.remote_i2c.receiver.score import edges, expand
from experiments.remote_onewire.score import DRIVE, HALT, LINK, MASK, PROGRAM, TARGET

PERIOD_NS = 200
COMMAND = (0xcc, 0xb4)


def command_bytes(bits):
    return [sum(b << i for i, b in enumerate(bits[start:start+8])) for start in (0, 8)]


def wire_samples(values):
    # Recover slot origins from the input alone. A responding zero can introduce
    # a second pull-down in the same read slot after the controller lets go.
    transitions = edges(values, LINK)
    need(len(transitions) >= 38 and not len(transitions) % 2, "complete DQ19 low pulses")
    pulses = list(zip(transitions[::2], transitions[1::2]))
    reset, presence = pulses[:2]
    need(2400 <= reset[1] - reset[0] <= 2550, "physical low during reset")
    gap_ns = (presence[0] - reset[1]) * PERIOD_NS
    width_ns = (presence[1] - presence[0]) * PERIOD_NS
    need(15_000 <= gap_ns <= 60_000 and 60_000 <= width_ns <= 240_000, "physical presence window")
    groups = []
    for start, end in pulses[2:]:
        if not groups or (start - groups[-1][0][0]) * PERIOD_NS >= 70_000:
            groups.append([])
        groups[-1].append((start, end))
    need(len(groups) == 17 and all(len(g) == 1 for g in groups[:16]), "sixteen raw writes and one read")
    starts = [group[0][0] for group in groups]
    return starts, dict(reset_low_ns=(reset[1] - reset[0]) * PERIOD_NS, presence_delay_ns=gap_ns,
                        presence_width_ns=width_ns, final_slot_low_pulses=len(groups[-1]))


def measure(changes, meta, trial):
    delay, reply, match = trial
    need([meta["delay_us"], meta["bit"], meta["match"]] == list(trial) and meta["samples"] == 15000,
         "physical workload")
    need(meta["before"] == meta["at_halt"] == meta["released"] == [1, 1], "both inputs idle before and after")
    values = expand(changes, meta["samples"], MASK)
    need((values[0] & MASK) == LINK | TARGET and (values[-1] & MASK) == LINK | TARGET | HALT, "idle capture boundaries")
    starts, result = wire_samples(values)
    bits = [(byte >> i) & 1 for byte in COMMAND for i in range(8)]
    command_edges = edges(values, DRIVE)
    halts = edges(values, HALT)
    need(len(command_edges) == 36 and len(halts) == 1, "18 pulls including reset and one HALT")
    falls, releases = command_edges[::2], command_edges[1::2]
    durations = [(b - a) * PERIOD_NS for a, b in zip(falls, releases)]
    expected_ns = [500_000] + [2_000 if b else 62_000 for b in bits] + [2_000]
    need(all(abs(actual - expected) <= PERIOD_NS for actual, expected in zip(durations, expected_ns)),
         "reset duration and every open-drain command width")
    slot_spacings = [(b - a) * PERIOD_NS for a, b in zip(falls[1:], falls[2:])]
    need(all(abs(x - 76_000) <= PERIOD_NS for x in slot_spacings), "76 us controller slot spacing")
    need(all(abs(a-b) <= 2 for a, b in zip(falls[1:], starts)), "independently detected pin and command origins")
    need((halts[0] - falls[-1]) * PERIOD_NS >= 60_000, "final slot duration")
    expected_bit = reply if match else 1
    for pin, mask in (("gpio19", LINK), ("gpio27", TARGET)):
        sampled = [int(bool(values[start + 120] & mask)) for start in starts[:16]]  # 24 us
        observed = command_bytes(sampled)
        read_bit = int(bool(values[starts[16] + 75] & mask))  # 15 us
        need(observed == list(COMMAND) and read_bit == expected_bit, pin + " independently sampled command and response")
        need(all(values[t] & mask for t in range(halts[0], len(values))), pin + " idle after HALT")
        result[pin] = dict(command=observed, read_bit=read_bit, transitions=len(edges(values, mask)))
    need(not (values[starts[-1] + 75] & DRIVE), "controller release command at read sample")
    need(meta["peer_fifo"] == [0xb4cc0000, 1 if match else 2], "hardware peer command capture and accept/reject")
    need(meta["status"] == (0x88 if expected_bit else 0x90), "firmware result on dedicated outputs")
    result.update(requested_presence_delay_us=delay, requested_reply=reply, matched=match, marker=meta["status"],
                  peer_fifo=meta["peer_fifo"], slots=len(starts), reset_command_ns=durations[0],
                  short_command_ns=sorted(set(d for d, b in zip(durations[1:17], bits) if b)),
                  long_command_ns=sorted(set(d for d, b in zip(durations[1:17], bits) if not b)),
                  read_command_ns=durations[-1], spacing_ns=sorted(set(slot_spacings)),
                  read_start_to_halt_ns=(halts[0] - falls[-1]) * PERIOD_NS)
    return result


def records(path):
    raw = gzip.decompress(path.read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "complete physical terminal")
    stdout, stderr = raw[2:-2].split(b"\x04", 1)
    need(not stderr, "clean peer execution")
    rows = [json.loads(line[7:]) for line in stdout.splitlines() if line.startswith(b"I2CLAB ")]
    start, end = rows[0], rows[-1]
    need(start["protocol"] == "onewire-peer" and start["system_hz"] == 125000000 and start["core_divisor"] == 10
         and [start[k] for k in ("peer_hz", "sample_hz", "gpio_base", "in_base", "mask")] == [1000000, 5000000, 16, 19, MASK],
         "shared clock and sampled pins")
    need(end["event"] == "finish" and end["restored_hz"] == start["original_hz"] and end["restored_bank"]
         and end["host_uio_oe"] == 0, "restored fixture")
    changes, metadata = {}, {}
    for row in rows[1:-1]:
        name = row["name"]
        if row["event"] == "cold":
            need(name not in changes and row["rows"] == 712 and row["registers"] == [[160, 85], [161, 0], [164, 0]]
                 and hashlib.sha256(bytes.fromhex(row["image"])).hexdigest() == PROGRAM, "exact firmware receipt")
            changes[name] = []
        elif row["event"] == "pins":
            need(name in changes and name not in metadata and row["changes"], "complete pin fragments")
            changes[name].extend(row["changes"])
        else:
            need(row["event"] == "trace" and name in changes and name not in metadata, "one record per load")
            metadata[name] = row
    need(list(changes) == list(metadata) == [str(i) for i in range(6)], "six ordered board loads")
    return changes, metadata


def score(path):
    # The independent oracle states all six requested conditions explicitly.
    trials = [(25, 1, True), (55, 0, True), (25, 0, True), (55, 1, True), (25, 0, False), (55, 0, False)]
    changes, meta = records(path)
    return {name: measure(changes[name], meta[name], trials[int(name)]) for name in meta}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("terminal", type=Path)
    print(json.dumps(score(p.parse_args().terminal), indent=2))
