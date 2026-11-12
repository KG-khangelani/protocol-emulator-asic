# SPDX-License-Identifier: Apache-2.0
"""Qualify the exact D38 chip with unchanged public expectations and store properties."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from store_lanes import build, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate", choices=("selection", "store"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated build output required")
    out.mkdir(parents=True)
    manifest = build(out / "variants")

    def run(script, *options):
        subprocess.run([sys.executable, str(ROOT / "experiments/i2c" / script), *map(str, options)], cwd=ROOT, check=True)

    def read(path):
        return json.loads(path.read_bytes())

    result = {"status": "RUNNING", "gate": args.gate, "implementation": "od128-lanes", "sources": manifest,
              "physical": "NOT_EVALUATED", "production": "UNCHANGED"}
    def save():
        (out / "result.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    save()
    try:
        if args.gate == "selection":
            run("run_physical_selection.py", "--variants", out / "variants", "--output", out / "selection",
                "--source-revision", "explicit-lanes")
            selection = read(out / "selection/result.json")
            assert selection["status"] == "PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS"
            assert selection["sources"] == manifest["od128"]["source_sha256"]
            result["status"] = "PASS_LANES_PUBLIC_SELECTION"
        else:
            run("run_store_local_proof.py", "--variants", out / "variants", "--output", out / "store",
                "--variant", "od128", "--lane-style", "explicit")
            assert read(out / "store/result.json")["status"] == "PASS_SELECTED_STORE_TASKS"
            run("audit_store_proofs.py", "--positive", out / "store", "--controls", out / "store",
                "--variant", "od128", "--source-revision", "explicit-lanes", "--output", out / "audit/od128.json")
            audit = read(out / "audit/od128.json")
            assert audit["status"] == "PASS_COMPLETE_VARIANT_STORE_PROOF"
            assert audit["source_sha256"] == manifest["od128"]["source_sha256"]["m1_program_store.v"]
            run("falsify_store_audit.py", "--positive", out / "store", "--controls", out / "store",
                "--snapshot", out / "audit/od128.positive.json", "--source-revision", "explicit-lanes",
                "--output", out / "audit/auditor-controls.json")
            assert read(out / "audit/auditor-controls.json")["status"] == "PASS_AUDITOR_NEGATIVE_CONTROLS"
            result["status"] = "PASS_LANES_AUDITED_STORE"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
