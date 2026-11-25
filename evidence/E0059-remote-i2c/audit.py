# SPDX-License-Identifier: Apache-2.0
"""Reconstruct the remote I2C conclusions and check the restoration and rebuild records."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import check, need
from experiments.remote_i2c.remote import IMAGE_SHA
from tools.production_sram import verify


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(verify_payloads):
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    for base, section in ((ROOT, "inputs"), (HERE, "files")):
        for name, expected in manifest[section].items():
            need(sha(base / name) == expected, section + " " + name)
    profile = verify(ROOT)
    need(sha(HERE / "fabricfox.bin") == IMAGE_SHA, "FPGA bitstream")
    routes = [json.loads((HERE / name).read_bytes()) for name in ("route-a.json", "route-b.json")]
    need(routes[0] == routes[1] and routes[0]["image_sha256"] == IMAGE_SHA
         and routes[0]["profile_sha256"] == profile["profile_sha256"], "two strict builds")
    for name, expected in routes[0]["source_sha256"].items():
        need(sha(ROOT / name) == expected, name)
    need(routes[0]["clock"]["constraint"] == 12.5 and routes[0]["clock"]["achieved"] >= 12.5, "route timing")
    attempts = HERE / "initial"
    first = json.loads((attempts / "allocation-result.json").read_bytes())
    output = gzip.decompress((attempts / "allocation-terminal.bin.gz").read_bytes())
    need(first["status"] == "INCOMPLETE" and "MemoryError" in first["error"] and output.count(b'"event": "trace"') == 3,
         "first incomplete capture")
    recovery = json.loads((attempts / "soft-restore.json").read_bytes())
    need(recovery["soft_restart"]["returned_to_prompt"] and recovery["after"] == "tt_um_factory_test",
         "stock board selection after interrupted restoration")
    total = strict = diagnostic = acknowledgments = 0
    for name in ("native-first", "linked-pulls", "native-repeat"):
        directory = HERE / name
        rec = json.loads((directory / "result.json").read_bytes())
        need(rec["traces"] == 6 and rec["image_sha256"] == IMAGE_SHA
             and rec["identity_sha256"] == manifest["board_identity_sha256"], name + " fixture")
        if name == "native-first":
            need(rec["status"] == "INCOMPLETE" and "502" in rec["error"], "recoverable gallery error")
        else:
            need(rec["status"] == "CAPTURED" and rec["after"] in ("idle_display", "tt_um_factory_test")
                 and rec["linked_pulls"] == (name == "linked-pulls"), name + " completion")
            if verify_payloads:
                from experiments.remote_i2c.remote import board_code
                need(hashlib.sha256(board_code(rec["linked_pulls"])).hexdigest() == rec["code_sha256"], name + " uploaded code")
        result = check(directory / "terminal.bin.gz")
        expected = json.loads((directory / "decoded.json").read_bytes())
        need(json.loads(json.dumps(result)) == expected, name + " decoded archive")
        total += len(result)
        strict += sum(r["raw_wire"]["passed"] for r in result.values())
        diagnostic += sum(r["five_sample_diagnostic"]["passed"] for r in result.values())
        acknowledgments += sum(r["terminal_status"] == 0x88 for r in result.values())
    need((total, strict, diagnostic, acknowledgments) == (18, 0, 18, 12), "original raw and diagnostic results")
    print(f"{total} complete transfers, {acknowledgments} addressed reads, {total-acknowledgments} address NACKs; "
          f"{strict} clean raw decodes; {diagnostic} matched five-sample decodes")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify-payloads", action="store_true", help="reassemble the uploaded payload in the locked workbench")
    audit(p.parse_args().verify_payloads)
