# SPDX-License-Identifier: Apache-2.0
"""Replay the receiver captures, including the first late-service failure."""
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import need
from experiments.remote_i2c.stretch import score as capture
from experiments.remote_i2c.stretch.run import payload
from experiments.remote_i2c.remote import IMAGE_SHA, NAME
from tools.production_sram import verify


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def rejected(expected, action, *args):
    try:
        action(*args)
    except ValueError as error:
        need(str(error) == expected, "wrong reason for rejection: " + str(error))
        return
    raise ValueError("altered observation accepted: " + expected)


def negative_controls(path):
    cold, pins, traces = capture.records(path)
    name = "0--1"
    changes = pins[name]
    trace = traces[name]
    halt = next(t for t, pins_at_t in changes if pins_at_t & capture.HALT)
    early = [[t - 100 if t == halt else t, v] for t, v in changes]
    rejected("timeout outside project cleanup window", capture.measure, early, trace)
    # Insert a real positive clock sample while the archived receiver stayed low.
    t = halt - 200
    level = next(v for tick, v in reversed(changes) if tick < t)
    pulse = sorted(changes + [[t, level | capture.SCL], [t + 1, level]])
    rejected("single final stretched clock", capture.measure, pulse, trace)
    rejected("peripheral received register and read request", capture.measure, changes, dict(trace, pointer=0x97))
    bad = dict(cold[name], image="ff" + cold[name]["image"][2:])
    rejected(name + " physical cold readback", capture.check_load, bad, 0)
    rejected("terminal byte and complete native clocks", capture.measure, pins["0-0"], dict(traces["0-0"], rx=0))


def partial_session(path, receipt):
    data, stderr = capture.terminal(path)
    need("ValueError: ('native receiver idle', [0, 1])" in stderr.decode() and
         stderr.decode() == receipt["error"], "recorded receiver restart failure")
    completed = [row for row in data if row["event"] == "trace"]
    need([row["name"] for row in completed] == ["24-3850", "0-3850", "0-4150"] and
         data[-1]["event"] == "cold" and data[-1]["name"] == "24-4150", "partial capture boundary")
    for row in data:
        if row["event"] == "cold":
            capture.check_load(row, int(row["name"].split("-")[0]))
    results = {}
    for row in completed:
        changes = [edge for block in data if block["event"] == "pins" and block["name"] == row["name"]
                   for edge in block["changes"]]
        results[row["name"]] = capture.measure(changes, row)
    return results


def audit():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, label in ((ROOT, "inputs"), (HERE, "files")):
        for name, expected in manifest[label].items():
            need(sha((base / name).read_bytes()) == expected, "retained hash: " + name)
    profile = verify(ROOT)
    need(len(profile["files_sha256"]) == 20, "qualified production inputs")
    need(sha((ROOT / "evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) == IMAGE_SHA, "FPGA identity")
    retained = json.loads((HERE / "measurements.json").read_bytes())
    sessions = ("core-a", "boundary-a", "boundary-b", "boundary-c", "core-b", "boundary-d")
    seen, partial = {}, {}
    for name in sessions:
        suite = name.split("-")[0]
        receipt = json.loads((HERE / "sessions" / (name + ".json")).read_bytes())
        raw = HERE / "sessions" / (name + ".bin.gz")
        need(receipt["board"] == "fpga-4" and receipt["suite"] == suite and receipt["clients_before"] == 0 and
             receipt["identity_sha256"] == manifest["board_identity_sha256"] and receipt["image_sha256"] == IMAGE_SHA and
             receipt["profile_sha256"] == profile["profile_sha256"] and
             datetime.fromisoformat(receipt["started_utc"]) < datetime.fromisoformat(receipt["ended_utc"]),
             "session identity: " + name)
        original = name in ("core-a", "boundary-a", "boundary-b")
        version = "original" if original else "receiver-reset"
        job = gzip.decompress((HERE / "jobs" / (version + "-" + suite + ".py.gz")).read_bytes())
        need(sha(job) == receipt["code_sha256"], "executed board job: " + name)
        current = payload(suite)
        if original:
            source = (ROOT / "experiments/remote_i2c/stretch/on_board.py").read_text(encoding="utf8").encode()
            need(current.endswith(source), "current job body")
            prefix = current[:-len(source)]
            need(job.startswith(prefix) and sha(job[len(prefix):]) == manifest["original_board_source_sha256"],
                 "original job body with the same firmware plans and loader")
        else:
            need(job == current, "current acquisition job rebuild")
        if name == "boundary-a":
            need(receipt["status"] == "INCOMPLETE" and receipt["error"] == "board occupied before selection"
                 and "enable" not in receipt and not raw.exists(), "board admission refused before selection")
            continue
        need(receipt["enable"]["enabled"] == NAME and receipt["restore"]["enabled"] ==
             receipt["after"] == receipt["restore_target"] == "tt_um_factory_test", "configuration restoration")
        if name == "boundary-b":
            need(receipt["status"] == "INCOMPLETE" and "traces" not in receipt, "session stopped early")
            partial = partial_session(raw, receipt)
            continue
        need(receipt["status"] == "CAPTURED" and receipt["traces"] == 6, "six complete physical trials")
        events, _ = capture.terminal(raw)
        need(events[0].get("reset_each_receiver", False) == (not original) and
             events[0]["micropython"] == "1.30.0-preview", "physical acquisition version")
        seen[name] = capture.score(raw, suite)
    replay = json.loads(json.dumps(dict(complete=seen, partial=partial)))
    need(replay == retained, "all timing and decoded results reproduced from the terminal bytes")
    results = [case for suite in seen.values() for case in suite.values()]
    timeouts = [case for case in results if case["outcome"] == "TIMEOUT"]
    need(len(results) == 24 and len(timeouts) == 8 and all(case["interval_inside_contract"] for case in timeouts),
         "complete comparison and timeout interval")
    negative_controls(HERE / "sessions/core-b.bin.gz")
    print("PASS: 24 complete physical trials, 3 additional traces in the failed session, 5 rejected corruptions, "
          "4 job identities, 20 qualified production inputs")


if __name__ == "__main__":
    audit()
