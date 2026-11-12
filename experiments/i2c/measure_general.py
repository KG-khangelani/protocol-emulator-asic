# SPDX-License-Identifier: Apache-2.0
"""Measure whole-chip generic cost including every real program-store bit."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/spi_phase"))
from build_variants import FILES
from run_comparison import TOP, cell_counts


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("a new isolated build directory is required")
    out.mkdir(parents=True)
    variants = args.variants.resolve()
    result = {"status": "RUNNING", "scope": "GENERIC_WHOLE_CHIP_NOT_MAPPED_OR_ROUTED",
              "runner_sha256": digest(Path(__file__)), "measurements": {}, "sources": {}}

    def save():
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    save()
    try:
        for variant in ("compact10", "literal255", "od128"):
            src = variants / ("legacy/compact10" if variant == "compact10" else variant) / "src"
            hashes = {n: digest(src/n) for n in FILES}
            result["sources"][variant] = hashes
            target = out / variant
            target.mkdir()
            netlist = target / "synth.json"
            script = "read_verilog " + " ".join(str(src/n) for n in FILES)
            script += f"; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {netlist}"
            start = time.monotonic()
            with (target/"synthesis.log").open("w") as log:
                p = subprocess.run(["yosys", "-Q", "-p", script], cwd=ROOT,
                                   stdout=log, stderr=subprocess.STDOUT, timeout=600)
            assert p.returncode == 0, f"{variant} synthesis failed"
            assert hashes == {n: digest(src/n) for n in FILES}, "source drift"
            result["measurements"][variant] = dict(cell_counts(netlist),
                seconds=round(time.monotonic()-start, 3), netlist_sha256=digest(netlist))
            save()
            print(variant, result["measurements"][variant], flush=True)
        result["status"] = "PASS_GENERIC_COST_ONLY"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
