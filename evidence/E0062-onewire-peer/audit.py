# SPDX-License-Identifier: Apache-2.0
"""Replay each physical 1-Wire sample stream and challenge the positive and negative trials."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import need
from experiments.remote_i2c.receiver.score import expand
from experiments.remote_i2c.remote import IMAGE_SHA
from experiments.remote_onewire.peer.score import measure, records, score, wire_samples
from experiments.remote_onewire.score import MASK, PROGRAM, TARGET
from tools.production_sram import verify


def reject(changes, meta, trial, expected):
    try:
        measure(changes, meta, trial)
    except ValueError as err:
        need(str(err) == expected, "unexpected rejection " + str(err))
    else:
        raise ValueError("accepted altered evidence: " + expected)


def tamper_checks(path):
    changes, meta = records(path)
    reject(changes["4"], {**meta["4"], "peer_fifo": [0xb4cc0000, 1]}, (25, 0, False),
           "hardware peer command capture and accept/reject")
    reject(changes["1"], {**meta["1"], "status": 0x88}, (55, 0, True), "firmware result on dedicated outputs")
    pin = expand(changes["1"], meta["1"]["samples"], MASK)
    starts, _ = wire_samples(pin)
    pin[starts[-1] + 75] ^= TARGET
    altered = [[t, value] for t, value in enumerate(pin) if t == 0 or value != pin[t-1]]
    reject(altered, meta["1"], (55, 0, True), "gpio27 independently sampled command and response")


def audit(rebuild_job):
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, key in ((HERE, "files"), (ROOT, "inputs")):
        for name, expected in manifest[key].items():
            need(hashlib.sha256((base / name).read_bytes()).hexdigest() == expected, name)
    need(verify(ROOT)["profile_sha256"] == manifest["profile_sha256"], "qualified physical inputs")
    check = json.loads((HERE / "check-receipt.json").read_bytes())
    check_log = gzip.decompress((HERE / "check.log.gz").read_bytes())
    need(check["status"] == "PASS" and all(c["returncode"] == 0 for c in check["commands"])
         and hashlib.sha256(check_log).hexdigest() == check["artifact_sha256"]["run.log"], "repository checks")
    job = gzip.decompress((HERE / "job.py.gz").read_bytes())
    if rebuild_job:
        from experiments.remote_onewire.peer.run import payload
        need(payload() == job, "exact uploaded peer and cold loader")
    saved = json.loads((HERE / "measurements.json").read_bytes())
    need(set(saved) == {"first", "repeat"}, "two complete physical sessions")
    ids = set()
    for name in ("first", "repeat"):
        folder = HERE / name
        receipt = json.loads((folder / "result.json").read_bytes())
        need(receipt["status"] == "CAPTURED" and receipt["traces"] == 6 and receipt["board"] == "fpga-4"
             and receipt["clients_before"] == 0 and receipt["after"] == "tt_um_factory_test"
             and receipt["profile_sha256"] == manifest["profile_sha256"] and receipt["image_sha256"] == IMAGE_SHA
             and receipt["program_sha256"] == PROGRAM and hashlib.sha256(job).hexdigest() == receipt["code_sha256"],
             name + " physical run and restoration receipt")
        ids.add(receipt["identity_sha256"])
        path = folder / "terminal.bin.gz"
        need(score(path) == saved[name], name + " offline wire decoding and peer FIFO")
        tamper_checks(path)
    need(ids == {manifest["board_identity_sha256"]}, "physical board identity")
    print("12 physical 17-slot queries replayed. Both commands and eight active-peer replies matched. "
          "All four mismatched command filters left the wire high. Three altered records per session were rejected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-job", action="store_true")
    audit(parser.parse_args().rebuild_job)
