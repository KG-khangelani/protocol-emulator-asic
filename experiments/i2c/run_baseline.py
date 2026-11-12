# SPDX-License-Identifier: Apache-2.0
"""Measure existing compact10 public kernels without modifying any RTL."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/spi_phase"))
from build_timed_gpio import build
from build_variants import FILES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("a new build directory is required; preserve previous attempts")
    out.mkdir(parents=True)
    paths = [ROOT/"src"/n for n in FILES] + [ROOT/p for p in (
        "experiments/i2c/baseline_programs.py", "experiments/i2c/run_baseline.py",
        "test/test_i2c_baseline_public.py", "test/test.py", "test/Makefile", "test/tb.v",
        "experiments/spi_phase/build_variants.py", "experiments/spi_phase/build_timed_gpio.py",
        "tools/m1_contract_model.py", "docs/specs/p-i2c-controller-100k.md",
        "tools/workbench/toolchain.lock.json")]
    inputs = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    result = {"status": "RUNNING", "scope": "EXISTING_ISA_PUBLIC_KERNELS_NOT_FULL_I2C",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "parent_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "input_sha256": inputs, "sources": build(out/"variants"), "stages": [],
              "physical": "NO_NEW_RUN", "formal": "NOT_EVALUATED"}

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        pair = []
        for simulator, identity in (("icarus", "Running on Icarus Verilog"),
                                    ("verilator", "Running on Verilator")):
            path = out/simulator
            path.mkdir()
            env = dict(os.environ)
            for key in ("COCOTB_TEST_FILTER", "COCOTB_TESTCASE", "GATES", "MAKEFLAGS"):
                env.pop(key, None)
            env["I2C_BASELINE_RECORD_DIR"] = str(path/"records")
            command = ["make", "-C", "test", "SIM="+simulator,
                       "SRC_DIR="+str(out/"variants/compact10/src"),
                       "COCOTB_TEST_MODULES=test_i2c_baseline_public", "COCOTB_TEST_FILTER=",
                       "SIM_BUILD="+str(path/"sim"), "COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                       "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
            started = time.monotonic()
            with (path/"run.log").open("w") as log:
                process = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=600)
            log = (path/"run.log").read_text()
            cases = list(ET.parse(path/"results.xml").getroot().iter("testcase"))
            failed = [c.get("name") for c in cases if c.find("failure") is not None or c.find("error") is not None]
            skipped = [c.get("name") for c in cases if c.find("skipped") is not None]
            stage = {"simulator": simulator, "observed_identity": identity in log,
                     "command": command, "returncode": process.returncode,
                     "seconds": round(time.monotonic()-started, 3), "tests": len(cases),
                     "failed": failed, "skipped": skipped}
            stage["status"] = "PASS" if (process.returncode == 0 and identity in log and
                                            len(cases) == 2 and not failed and not skipped) else "FAIL"
            result["stages"].append(stage)
            save()
            print(simulator, stage["status"], flush=True)
            if stage["status"] != "PASS":
                raise RuntimeError(f"{simulator} failed; inspect {path/'run.log'}")
            records = [json.loads(line) for line in (path/"records/cases.jsonl").read_text().splitlines()]
            assert len(records) == 10
            pair.append(records)
        assert pair[0] == pair[1], "public record/trace hashes differ between simulators"
        assert inputs == {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}, "source drift"
        result.update(status="PASS_SCOPED_KERNELS_AND_RETAINED_LIMITS", cross_simulator_records_identical=True,
                      public_records_per_simulator=10, timeout_cleanup_kernel_words=10,
                      literal_write_schedule_words=122, real_capacity_words=10,
                      expected_protocol_failures=["Plain WAIT_PIN timeout holds SDA in FAULT",
                                                  "WAIT_PIN timeout skip inside LOOP holds SDA in FAULT",
                                                  "Literal success-wire schedule exceeds store and PC capacity"])
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
