# SPDX-License-Identifier: Apache-2.0
"""Verify the exact eighteen-group G2 netlist selection on generated RTL."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import physical_g2 as physical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", choices=("e35", "explicit-lanes", "shared-read"), default="e35")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated output required")
    out.mkdir(parents=True)
    src = args.variants.resolve() / "od128/src"
    implementation = {"e35": "od128", "explicit-lanes": "od128-lanes", "shared-read": "od128-shared"}[args.source_revision]
    sources = physical.verify_sources(src, implementation)
    result = {"status": "RUNNING", "sources": sources, "stages": [],
              "scope": "EXACT_G2_PHYSICAL_SELECTION_ON_RTL", "physical": "NOT_EVALUATED"}
    physical.write_json(out / "result.json", result)
    try:
        for simulator in ("icarus", "verilator"):
            stage = out / simulator
            stage.mkdir()
            env = dict(os.environ, G2_PHYSICAL="yes", I2C_GENERAL_VARIANT="od128",
                       I2C_GENERAL_RECORD_DIR=str(stage / "records/i2c"), I2C_GENERAL_SMOKE="0",
                       TIMED_GPIO_VARIANT="compact10", TIMED_GPIO_RECORD_DIR=str(stage / "records/spi"),
                       TIMED_GPIO_SMOKE="0", COCOTB_RANDOM_SEED="20261112")
            for key in ("GATES", "G1_PHYSICAL", "MAKEFLAGS", "COCOTB_TESTCASE", "COCOTB_TEST_FILTER"):
                env.pop(key, None)
            command = ["make", "-C", "test", "SIM=" + simulator, "SRC_DIR=" + str(src),
                       "SIM_BUILD=" + str(stage / "sim"), "COCOTB_RESULTS_FILE=" + str(stage / "results.xml"),
                       "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
            start = time.monotonic()
            with (stage / "run.log").open("w") as log:
                proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            assert proc.returncode == 0, "simulation failed"
            assert ("Running on Icarus Verilog" if simulator == "icarus" else "Running on Verilator") in (stage / "run.log").read_text()
            physical.check_tests(SimpleNamespace(junit=stage / "results.xml", records=stage / "records",
                                                 output=stage / "check.json", require_netlist=False))
            result["stages"].append({"simulator": simulator, "command": command,
                                     "returncode": proc.returncode, "seconds": round(time.monotonic() - start, 3),
                                     "check": physical.read_json(stage / "check.json")})
            physical.write_json(out / "result.json", result)
        assert physical.verify_sources(src, implementation) == sources
        result["status"] = "PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS"
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        physical.write_json(out / "result.json", result)


if __name__ == "__main__":
    main()
