# SPDX-License-Identifier: Apache-2.0
"""Score the measured reset, drive state, observed DQ and HALT in the six physical controls."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import need
from experiments.remote_i2c.receiver.score import edges, expand

MASK = 0x8901
LINK, TARGET, HALT, DRIVE = (1, 0x100, 0x800, 0x8000)
MODES = ("absent", "stuck-before", "stuck-after", "stuck-after", "stuck-before", "absent")
PROGRAM = "a29b2e045146fb1c29121a616f692ebd43142b55ab73baae9f1148b977e14638"


def measure(changes, meta):
    mode = meta["mode"]
    need(meta["samples"] == 15000 and meta["status"] == 0x98, "error marker and terminal release")
    need(meta["before"] == meta["released"] == [1, 1], "idle before and after the injected condition")
    need(meta["at_launch"] == [int(mode != "stuck-before")] * 2 and meta["held"] == [int(mode == "absent")] * 2,
         "two independent input readings at launch and HALT")
    samples = expand(changes, meta["samples"], MASK)
    cmd, halt = edges(samples, DRIVE), edges(samples, HALT)
    need(len(halt) == 1 and not samples[0] & (HALT | DRIVE) and samples[-1] & HALT and not samples[-1] & DRIVE,
         "release at terminal marker and one HALT")
    need(len(cmd) == (0 if mode == "stuck-before" else 2), "no command slots and correct reset count")
    metrics = dict(mode=mode, status=meta["status"], drive_edges=cmd, halt_sample=halt[0], command_slots=0)
    if not cmd:
        need(all(not value & (LINK | TARGET) for value in samples), "both inputs saw the pre-existing low")
        return metrics
    start, release = cmd
    low_ns = (release - start) * 200
    need(samples[start] & DRIVE and not samples[release] & DRIVE and abs(low_ns - 500_000) <= 200
         and release < halt[0], "commanded 500 us reset")
    metrics.update(reset_low_ns=low_ns, reset_start_to_halt_ns=(halt[0] - start) * 200)
    for name, bit in (("gpio19", LINK), ("gpio27", TARGET)):
        transitions = edges(samples, bit)
        need(transitions and not samples[transitions[0]] & bit and abs(transitions[0] - start) <= 1, name + " reset assertion")
        need(not any(samples[t] & bit for t in range(start + 1, release)), name + " held low during reset")
        metrics[name + "_transitions"] = transitions
        if mode == "absent":
            first_high = next((t for t in range(release, halt[0]) if samples[t] & bit), None)
            need(first_high is not None and all(value & bit for value in samples[halt[0]:]), name + " pulled-up line after release")
            metrics[name + "_first_high_after_release_ns"] = (first_high - release) * 200
        else:
            need(all(not value & bit for value in samples[release:]), name + " external hold after the FPGA released")
    return metrics


def score(path):
    raw = gzip.decompress(path.read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "complete raw terminal")
    stdout, stderr = raw[2:-2].split(b"\x04", 1)
    need(not stderr, "board exception")
    data = [json.loads(s[7:]) for s in stdout.splitlines() if s.startswith(b"I2CLAB ")]
    start, end = data[0], data[-1]
    need(start["event"] == "start" and start["protocol"] == "1-wire-controls"
         and [start[k] for k in ("system_hz", "clock_divisor", "sample_hz", "gpio_base", "in_base", "mask")]
         == [125000000, 10, 5000000, 16, 19, MASK], "physical clocks and pins")
    need(end["event"] == "finish" and end["host_uio_oe"] == 0 and end["restored_bank"]
         and end["restored_hz"] == start["original_hz"], "fixture cleanup")
    pins, results = {}, {}
    for r in data[1:-1]:
        name = r["name"]
        if r["event"] == "cold":
            binary = bytes.fromhex(r["image"])
            need(name not in pins and len(binary) == 340 and hashlib.sha256(binary).hexdigest() == PROGRAM
                 and r["rows"] == 712 and r["registers"] == [[160, 85], [161, 0], [164, 0]], name + " cold readback")
            pins[name] = []
        elif r["event"] == "pins":
            need(name in pins and name not in results and r["changes"], name + " pin fragment")
            pins[name].extend(r["changes"])
        else:
            need(r["event"] == "trace" and name in pins and name not in results
                 and name == f"{len(results)}-{MODES[len(results)]}" and r["mode"] == MODES[len(results)], name + " trial")
            results[name] = measure(pins[name], r)
    need(len(results) == 6 and set(results) == set(pins), "complete physical controls")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terminal", type=Path)
    print(json.dumps(score(parser.parse_args().terminal), indent=2))
