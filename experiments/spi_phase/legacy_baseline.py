# SPDX-License-Identifier: Apache-2.0
"""Read the immutable E0020 inputs used by historical SPI/G2 experiments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = Path(__file__).resolve().parent / "baseline"
FILES = ("project.v", "m1_engine.v", "m1_program_store.v", "m1_data_store.v", "m1_input_sync.v")


def baseline_inputs():
    return [BASELINE/name for name in FILES] + [Path(__file__).resolve(), BASELINE/"manifest.json"]


def baseline_sources():
    manifest = json.loads((BASELINE/"manifest.json").read_text(encoding="utf-8"))
    evidence = json.loads((ROOT/"evidence/E0020-spi-mode0-feasibility/result.json").read_text(encoding="utf-8"))
    expected = {name: evidence["unchanged_source_sha256"]["src/"+name] for name in FILES}
    if manifest["source_sha256"] != expected or manifest["source_commit"] != evidence["base_head"]:
        raise ValueError("frozen baseline manifest differs from E0020")
    result = {}
    for name in FILES:
        raw = (BASELINE/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected[name]:
            raise ValueError("frozen E0020 baseline drift: " + name)
        result[name] = raw.decode("utf-8")
    return result
