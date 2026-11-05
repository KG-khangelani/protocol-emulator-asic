# SPDX-License-Identifier: Apache-2.0
"""Run isolated complete-chip comparisons in the already locked workbench."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from build_variants import ROOT, FILES, build

TOP = "tt_um_khangelani_protocol_emulator"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell_counts(path):
    modules = json.loads(path.read_text())["modules"]
    counts = Counter()

    def visit(name):
        for cell in modules[name].get("cells", {}).values():
            kind = cell["type"]
            if kind in modules:
                visit(kind)
            else:
                counts[kind] += 1
    visit(TOP)
    assert not any("LATCH" in kind.upper() for kind in counts), counts
    return {"primitive_cells": sum(counts.values()),
            "state_bits": sum(n for k, n in counts.items() if "DFF" in k.upper()),
            "cell_types": dict(sorted(counts.items()))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT / "build/spi-phase-comparison" / stamp).resolve()
    if output.exists():
        raise ValueError("refuse to overwrite an earlier attempt")
    before = {"src/" + name: sha(ROOT / "src" / name) for name in FILES}
    sources = build(output)
    inputs = sorted((ROOT / "experiments/spi_phase").glob("*.py")) + [
        ROOT / "test/Makefile", ROOT / "test/tb.v", ROOT / "test/test.py",
        ROOT / "test/test_uart_rx_public.py", ROOT / "test/test_spi_mode0_public.py",
        ROOT / "test/test_spi_phase_comparison.py",
        ROOT / "tools/spi_mode0_oracle.py", ROOT / "docs/specs/spi-phase-comparison.md"]
    input_hashes = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    result = {"status": "RUNNING", "rung": "EXPERIMENTAL_RTL_GENERIC_SYNTHESIS",
              "output": str(output), "production_sha256": before, "stages": [],
              "measurements": {}, "sources": sources, "input_sha256": input_hashes}
    env = dict(os.environ)
    for key in ("COCOTB_TEST_FILTER", "COCOTB_TESTCASE", "GATES", "MAKEFLAGS"):
        env.pop(key, None)
    env["PYTHONPATH"] = str(ROOT / "experiments/spi_phase") + os.pathsep + str(ROOT)

    def save():
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    def run(label, command, *, expected_failures=None, junit=None, count=None):
        log = output / (label + ".log")
        started = time.monotonic()
        with log.open("w") as stream:
            try:
                proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                      stderr=subprocess.STDOUT, timeout=600)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = 124
        stage = {"name": label, "command": command, "returncode": code,
                 "seconds": round(time.monotonic() - started, 3), "log": log.name}
        ok = code == 0
        if junit is not None:
            stage["junit"] = str(junit.relative_to(output))
            if junit.exists():
                cases = list(ET.parse(junit).getroot().iter("testcase"))
                failed = sorted(c.get("classname", "") + "." + c.get("name", "")
                                for c in cases if c.find("failure") is not None or c.find("error") is not None)
                skipped = [c for c in cases if c.find("skipped") is not None]
                stage.update(cases=len(cases), failures=failed, skipped=len(skipped))
                ok = len(cases) == count and not skipped and failed == (expected_failures or [])
                ok = ok and ((code != 0) if expected_failures else code == 0)
            else:
                ok = False
        stage["status"] = "PASS" if ok else "FAIL"
        if expected_failures:
            stage["compatibility"] = "FAIL_EXPECTED_AND_RETAINED"
        result["stages"].append(stage)
        save()
        print(label, stage["status"], flush=True)
        if not ok:
            raise RuntimeError(f"{label} failed; inspect {log}")

    def simulate(variant, simulator, modules, label, count, expected=None, test_filter=""):
        directory = output / variant
        junit = directory / (label + ".xml")
        env["PHASE_COMPARE_VARIANT"] = variant
        run(variant + "-" + label,
            ["make", "-C", "test", "SIM=" + simulator,
             "SRC_DIR=" + str(directory / "src"), "COCOTB_TEST_MODULES=" + modules,
             "PYTHONPATH=" + env["PYTHONPATH"],
             "COCOTB_TEST_FILTER=" + test_filter,
             "SIM_BUILD=" + str(directory / "sim" / simulator),
             "COCOTB_RESULTS_FILE=" + str(junit), "FST=", "COCOTB_PLUSARGS=+NO_DUMP"],
            junit=junit, count=count, expected_failures=expected)

    save()
    try:
        run("reference", [sys.executable, "-m", "unittest", "discover", "-s",
                          "experiments/spi_phase", "-p", "test_reference.py", "-v"])
        for variant in sources:
            simulate(variant, "icarus", "test,test_uart_rx_public", "legacy", 17,
                     ["test.invalid_length_never_releases_engine"] if variant == "banked" else None)
            if variant == "baseline":
                simulate(variant, "icarus", "test_spi_mode0_public", "counterexample", 2)
            else:
                for simulator in ("icarus", "verilator"):
                    simulate(variant, simulator, "test_spi_phase_comparison",
                             "phase-" + simulator, 4)
            directory = output / variant
            netlist = directory / "synth.json"
            script = "read_verilog " + " ".join(str(directory / "src" / n) for n in FILES)
            script += f"; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {netlist}"
            run(variant + "-synth", ["yosys", "-Q", "-p", script])
            result["measurements"][variant] = cell_counts(netlist)
            save()
        assert before == {"src/" + n: sha(ROOT / "src" / n) for n in FILES}
        assert input_hashes == {str(p.relative_to(ROOT)): sha(p) for p in inputs}
        result["status"] = "PASS"
    except Exception as error:
        result["status"] = "FAIL"
        result["error"] = str(error)
        raise
    finally:
        save()
        print(output, flush=True)


if __name__ == "__main__":
    main()
