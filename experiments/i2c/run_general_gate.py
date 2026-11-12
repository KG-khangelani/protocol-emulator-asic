# SPDX-License-Identifier: Apache-2.0
"""CI entry point with strict result statuses and matching generated RTL."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gate", choices=("od128", "literal255", "architecture", "physical-selection"), required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)

    def run(script, target, expected, *options):
        subprocess.run([sys.executable, str(ROOT/"experiments/i2c"/script),
                        "--output", str(target), *options], cwd=ROOT, check=True)
        result = json.loads((target/"result.json").read_text())
        assert result["status"] == expected, (script, result["status"])
        return result

    if args.gate in ("od128", "literal255"):
        run("run_general.py", out/"protocols", "PASS_I2C_PUBLIC_MATRIX", "--variant", args.gate)
        return
    variants = out/"variants"
    subprocess.run([sys.executable, str(ROOT/"experiments/i2c/build_general.py"),
                    "--output", str(variants)], cwd=ROOT, check=True)
    options = ("--variants", str(variants))
    if args.gate == "physical-selection":
        run("run_physical_selection.py", out/"selection",
            "PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS", *options)
        return
    boundaries = run("run_general_boundaries.py", out/"boundaries", "PASS_PUBLIC_BOUNDARIES", *options)
    aborts = run("run_general_boundaries.py", out/"aborts", "PASS_PUBLIC_ABORT_AND_RELOAD", *options,
                 "--suite", "aborts", "--variant", "od128")
    formal = run("run_general_formal.py", out/"formal", "PASS_SCOPED_INSTRUCTION_PROOFS", *options)
    cost = run("measure_general.py", out/"cost", "PASS_GENERIC_COST_ONLY", *options)
    combined = run("run_combined_general.py", out/"combined", "PASS_LEGACY_PUBLIC_MATRIX", *options)
    manifest = json.loads((variants/"source-manifest.json").read_text())
    for variant in ("od128", "literal255"):
        sources = manifest[variant]["source_sha256"]
        assert boundaries["sources"][variant] == cost["sources"][variant] == sources
        assert formal["sources"][variant] == sources["m1_engine.v"]
    assert combined["source_sha256"] == manifest["od128"]["source_sha256"]
    assert aborts["sources"]["od128"] == manifest["od128"]["source_sha256"]
    (out/"result.json").write_text(json.dumps({"status": "PASS_SCOPED_ARCHITECTURE_GATE",
        "sources": manifest, "store_formal": "SEPARATE_PENDING_GATE",
        "physical": "NOT_EVALUATED", "production": "UNCHANGED"}, indent=2)+"\n")


if __name__ == "__main__":
    main()
