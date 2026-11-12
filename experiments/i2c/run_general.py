# SPDX-License-Identifier: Apache-2.0
"""Qualify isolated general I/O candidates against the frozen I2C oracle."""
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
from experiments.i2c.build_general import build
from build_variants import FILES
from legacy_baseline import baseline_inputs


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("od128", "literal255"), required=True)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("a new build directory is required; preserve previous attempts")
    out.mkdir(parents=True)
    paths = baseline_inputs() + [ROOT/p for p in (
        "experiments/i2c/public_bus.py", "experiments/i2c/run_general.py",
        "experiments/i2c/build_general.py", "experiments/i2c/general_programs.py",
        "experiments/i2c/baseline_programs.py", "experiments/spi_phase/phase_programs.py",
        "experiments/i2c/target.py", "tools/i2c_oracle.py", "test/test_i2c_general_public.py",
        "test/test.py", "test/Makefile", "test/tb.v",
        "experiments/spi_phase/build_variants.py", "experiments/spi_phase/build_timed_gpio.py",
        "tools/m1_contract_model.py", "docs/specs/p-i2c-controller-100k.md", "docs/specs/g2-general-io-candidate.md",
        "tools/workbench/toolchain.lock.json")]
    inputs = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    result = {"status": "RUNNING", "scope": "ISOLATED_GENERAL_CANDIDATE_PUBLIC_I2C_RTL",
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "parent_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "input_sha256": inputs, "sources": build(out/"variants"), "stages": [],
              "variant": args.variant, "smoke": args.smoke, "physical": "NO_NEW_RUN", "formal": "NOT_EVALUATED"}

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
            env["I2C_GENERAL_RECORD_DIR"] = str(path/"records")
            env["I2C_GENERAL_VARIANT"] = args.variant
            env["I2C_GENERAL_SMOKE"] = str(int(args.smoke))
            command = ["make", "-C", "test", "SIM="+simulator,
                       "SRC_DIR="+str(out/"variants"/args.variant/"src"),
                       "COCOTB_TEST_MODULES=test_i2c_general_public", "COCOTB_TEST_FILTER=",
                       "SIM_BUILD="+str(path/"sim"), "COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                       "FST=", "COCOTB_PLUSARGS=+NO_DUMP", "GENERAL_IO=yes"]
            started = time.monotonic()
            with (path/"run.log").open("w") as log:
                process = subprocess.run(command, cwd=ROOT, env=env, stdout=log,
                                         stderr=subprocess.STDOUT, timeout=1200)
            log = (path/"run.log").read_text()
            cases = list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
            failed = [c.get("name") for c in cases if c.find("failure") is not None or c.find("error") is not None]
            skipped = [c.get("name") for c in cases if c.find("skipped") is not None]
            stage = {"simulator": simulator, "observed_identity": identity in log,
                     "command": command, "returncode": process.returncode,
                     "seconds": round(time.monotonic()-started, 3), "tests": len(cases),
                     "failed": failed, "skipped": skipped}
            stage["status"] = "PASS" if (process.returncode == 0 and identity in log and
                                            len(cases) == 1 and not failed and not skipped) else "FAIL"
            result["stages"].append(stage)
            save()
            print(simulator, stage["status"], flush=True)
            if stage["status"] != "PASS":
                raise RuntimeError(f"{simulator} failed; inspect {path/'run.log'}")
            records = [json.loads(line) for line in (path/"records/cases.jsonl").read_text().splitlines()]
            assert len(records) == (32 if args.smoke else 1160)
            pair.append(records)
        assert pair[0] == pair[1], "public record/trace hashes differ between simulators"
        assert inputs == {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}, "source drift"
        result.update(status="PASS_I2C_SMOKE_ONLY" if args.smoke else "PASS_I2C_PUBLIC_MATRIX", cross_simulator_records_identical=True,
                      public_records_per_simulator=32 if args.smoke else 1160,
                      positives=26 if args.smoke else 1154, expected_negative=6,
                      limitation="Instruction/formal/combined-protocol/physical gates still pending")
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
