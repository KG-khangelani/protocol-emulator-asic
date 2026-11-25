# SPDX-License-Identifier: Apache-2.0
"""Audit the board's negative controls and the separate RTL transactions with the modeled sensor."""
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
from experiments.remote_i2c.remote import IMAGE_SHA
from experiments.remote_onewire.offline import inspect, score as score_rtl
from experiments.remote_onewire.program import image, source
from experiments.remote_onewire.score import PROGRAM, score as score_physical
from tools.assembler import program_bytes
from tools.production_sram import verify


def audit(rebuild_job):
    m = json.loads((HERE / "manifest.json").read_bytes())
    for base, key in ((HERE, "files"), (ROOT, "inputs")):
        for filename, expected in m[key].items():
            need(hashlib.sha256((base / filename).read_bytes()).hexdigest() == expected, filename)
    need(verify(ROOT)["profile_sha256"] == m["profile_sha256"], "production input verification")
    need((HERE / "board.asm").read_text() == source() and (HERE / "board.bin").read_bytes() == program_bytes(image())
         and image()["binary_sha256"] == PROGRAM, "assembled board program")
    load = json.loads((HERE / "board/result.json").read_bytes())
    job = gzip.decompress((HERE / "board/job.py.gz").read_bytes())
    need(load["status"] == "CAPTURED" and load["traces"] == 6 and load["image_sha256"] == IMAGE_SHA
         and load["program_sha256"] == PROGRAM and load["clients_before"] == 0
         and load["identity_sha256"] == m["board_identity_sha256"] and load["after"] == "tt_um_factory_test"
         and hashlib.sha256(job).hexdigest() == load["code_sha256"], "physical receipt")
    if rebuild_job:
        from experiments.remote_onewire.run import payload
        need(payload() == job, "exact uploaded board program")
    physical = score_physical(HERE / "board/terminal.bin.gz")
    need(physical == json.loads((HERE / "physical.json").read_bytes()), "physical reset, input and HALT evidence")
    rtl = json.loads((HERE / "rtl-result.json").read_bytes())
    runs = json.loads((HERE / "rtl-repeat.json").read_bytes())
    need([r["directory"] for r in runs] == ["onewire-rtl-a", "onewire-rtl-b"], "two fresh execution directories")
    logs = []
    for run in runs:
        need(run["result_sha256"] == m["files"]["rtl-result.json"], "identical independent execution summaries")
        logs.append(json.loads(gzip.decompress((HERE / run["log_archive"]).read_bytes())))
    need(rtl["status"] == "PASS" and rtl["profile_sha256"] == m["profile_sha256"] and rtl["core_hz"] == 12_500_000
         and rtl["images"]["normal"]["binary_sha256"] == PROGRAM and len(rtl["cases"]) == 12, "RTL execution")
    rejections = {}
    for name, case in rtl["cases"].items():
        raw_a, raw_b = [log[name] for log in logs]
        need(raw_a.replace("/onewire-rtl-a/", "/onewire-rtl-b/") == raw_b, name + " repeated RTL log")
        obs = inspect(raw_a)
        actual = score_rtl(obs, case["expected_marker"])
        need(obs == case["observed"] and actual == case["actual_rejection"] == case["expected_rejection"], name)
        if actual:
            rejections[name] = actual
    need(rejections == {"short-reset": "reset duration", "bad-command": "command bytes"}, "two protocol mutations")
    print("Six physical absent/stuck controls and two RTL runs verified. Each RTL run covered eight modeled power responses, two error paths and both mutations.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rebuild-job", action="store_true")
    audit(parser.parse_args().rebuild_job)
