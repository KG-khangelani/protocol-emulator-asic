# SPDX-License-Identifier: Apache-2.0
"""Execute public architectural boundaries on both actual simulators."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--variant", action="append", choices=("od128", "literal255"))
    p.add_argument("--suite", choices=("boundaries", "aborts"), default="boundaries")
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new build output required")
    out.mkdir(parents=True)
    inputs = [ROOT/s for s in ("test/test_general_boundaries.py", "test/test_i2c_general_public.py",
        "test/test.py", "test/Makefile", "test/tb.v", "experiments/i2c/general_programs.py",
        "experiments/i2c/baseline_programs.py", "experiments/spi_phase/phase_programs.py",
        "tools/m1_contract_model.py", "experiments/i2c/run_general_boundaries.py",
        "test/test_i2c_abort_public.py", "tools/i2c_oracle.py", "experiments/i2c/public_bus.py", "experiments/i2c/target.py")]
    result = {"status": "RUNNING", "scope": "PUBLIC_ARCHITECTURAL_BOUNDARIES",
              "input_sha256": {p.relative_to(ROOT).as_posix(): digest(p) for p in inputs},
              "sources": {}, "stages": [], "suite": args.suite}
    module = "test_general_boundaries" if args.suite == "boundaries" else "test_i2c_abort_public"
    expected_count = 4 if args.suite == "boundaries" else 1
    record_file = "boundaries.jsonl" if args.suite == "boundaries" else "aborts.jsonl"

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        for variant in args.variant or ("od128", "literal255"):
            src = args.variants.resolve()/variant/"src"
            result["sources"][variant] = {p.name: digest(p) for p in src.glob("*.v")}
            pair = []
            for sim, identity in (("icarus", "Running on Icarus Verilog"), ("verilator", "Running on Verilator")):
                path = out/(variant+"-"+sim)
                path.mkdir()
                env = dict(os.environ, I2C_GENERAL_VARIANT=variant, I2C_GENERAL_RECORD_DIR=str(path/"records"))
                for key in ("GATES", "MAKEFLAGS", "COCOTB_TESTCASE", "COCOTB_TEST_FILTER"):
                    env.pop(key, None)
                command = ["make", "-C", "test", "SIM="+sim, "SRC_DIR="+str(src),
                    "COCOTB_TEST_MODULES="+module, "COCOTB_TEST_FILTER=",
                    "SIM_BUILD="+str(path/"sim"), "COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                    "GENERAL_IO=yes", "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
                start = time.monotonic()
                with (path/"run.log").open("w") as log:
                    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=600)
                log = (path/"run.log").read_text()
                cases = list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
                failed = [c.get("name") for c in cases if any(c.find(n) is not None for n in ("failure", "error", "skipped"))]
                accepted = proc.returncode == 0 and len(cases) == expected_count and not failed and identity in log
                result["stages"].append(dict(variant=variant, simulator=sim, tests=len(cases), failed=failed,
                    command=command, returncode=proc.returncode, accepted=accepted, seconds=round(time.monotonic()-start, 3)))
                save()
                print(variant, sim, "PASS" if accepted else "FAIL", flush=True)
                assert accepted, f"{variant} {sim} boundaries failed"
                records = [json.loads(s) for s in (path/"records"/record_file).read_text().splitlines()]
                assert len(records) == (4 if args.suite == "boundaries" else 36)
                pair.append(records)
            assert pair[0] == pair[1], "boundary observations differ between simulators"
        assert result["input_sha256"] == {p.relative_to(ROOT).as_posix(): digest(p) for p in inputs}, "source drift"
        result.update(status="PASS_PUBLIC_BOUNDARIES" if args.suite == "boundaries" else "PASS_PUBLIC_ABORT_AND_RELOAD",
                      cross_simulator_identical=True)
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
