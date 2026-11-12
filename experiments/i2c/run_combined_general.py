# SPDX-License-Identifier: Apache-2.0
"""Run the unchanged qualified UART/SPI/public kernels on a G2 RTL candidate."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.physical_candidate import PUBLIC_TESTS, PUBLIC_TEST_MODULES, EXCLUDED_TESTS


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variants", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--reuse-icarus", type=Path, help="reuse a completed matching simulation after a result-parser failure")
    args = p.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build directory required")
    out.mkdir(parents=True)
    src = args.variants.resolve()/"od128/src"
    inputs = [ROOT/n for n in ("test/test.py", "test/test_uart_rx_public.py", "test/test_spi_timed_gpio.py",
        "test/Makefile", "test/tb.v", "experiments/spi_phase/timed_gpio_programs.py",
        "experiments/spi_phase/phase_programs.py", "experiments/spi_phase/four_mode_programs.py",
        "tools/m1_contract_model.py", "tools/spi_four_mode_oracle.py", "tools/spi_mode0_oracle.py",
        "tools/spi_phase_reference.py", "tools/uart_rx_oracle.py", "tools/uart_rx_host_service.py",
        "tools/physical_candidate.py", "experiments/i2c/run_combined_general.py")]
    source_hashes = {p.name: digest(p) for p in src.glob("*.v")}
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in inputs}
    result = {"status": "RUNNING", "variant": "od128", "source_sha256": source_hashes,
              "input_sha256": hashes, "stages": [],
              "scope": "LEGACY_PUBLIC_KERNELS_UART_BOUNDED_RX_AND_FOUR_MODE_SPI_ON_G2_RTL"}
    selected = {PUBLIC_TEST_MODULES[n]+"."+n for n in PUBLIC_TESTS}
    excluded = {module+"."+name for module, name in EXCLUDED_TESTS}
    baseline = ROOT/"evidence/E0030-timed-gpio-comparison/comparison/compact10/public-icarus/records/cases.jsonl.gz"
    reference = [json.loads(s) for s in gzip.decompress(baseline.read_bytes()).decode().splitlines()]
    reference = [r for r in reference if "trace_sha256" in r]
    result["spi_reference_sha256"] = digest(baseline)
    expression = "^("+"|".join(s.replace(".", r"\.") for s in sorted(selected))+")$$"

    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")

    save()
    try:
        pair = []
        for sim, identity in (("icarus", "Running on Icarus Verilog"), ("verilator", "Running on Verilator")):
            path = out/sim
            path.mkdir()
            env = dict(os.environ, TIMED_GPIO_VARIANT="compact10", TIMED_GPIO_RECORD_DIR=str(path/"records"), TIMED_GPIO_SMOKE="0")
            for key in ("GATES", "MAKEFLAGS", "COCOTB_TESTCASE", "COCOTB_TEST_FILTER"):
                env.pop(key, None)
            command = ["make", "-C", "test", "SIM="+sim, "SRC_DIR="+str(src),
                "COCOTB_TEST_MODULES=test,test_uart_rx_public,test_spi_timed_gpio", "COCOTB_TEST_FILTER='"+expression+"'",
                "SIM_BUILD="+str(path/"sim"), "COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                "GENERAL_IO=yes", "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
            start = time.monotonic()
            reuse = None
            if sim == "icarus" and args.reuse_icarus:
                previous = args.reuse_icarus.resolve()
                old = json.loads((previous/"result.json").read_text())
                assert old["source_sha256"] == source_hashes
                for name, sha in old["input_sha256"].items():
                    if name != "experiments/i2c/run_combined_general.py":
                        assert hashes[name] == sha, ("reused test input drift", name)
                old_stage = next(s for s in old["stages"] if s["simulator"] == "icarus")
                assert old_stage["returncode"] == 0
                for name in ("run.log", "results.xml"):
                    shutil.copyfile(previous/"icarus"/name, path/name)
                shutil.copytree(previous/"icarus/records", path/"records")
                returncode = 0
                reuse = dict(path=str(previous), result_sha256=digest(previous/"result.json"),
                             command=old_stage["command"], seconds=old_stage["seconds"])
            else:
                with (path/"run.log").open("w") as log:
                    proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=900)
                returncode = proc.returncode
            cases = list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
            names = {c.get("classname", "")+"."+c.get("name", "") for c in cases}
            failed = [c.get("name") for c in cases if any(c.find(n) is not None for n in ("failure", "error"))]
            skipped = {c.get("classname", "")+"."+c.get("name", "") for c in cases if c.find("skipped") is not None}
            accepted = (returncode == 0 and len(names) == len(cases) and names-skipped == selected
                        and skipped <= excluded and not failed and identity in (path/"run.log").read_text())
            result["stages"].append(dict(simulator=sim, command=command, returncode=returncode,
                tests=len(names-skipped), discovered=len(cases), names=sorted(names-skipped), excluded=sorted(skipped),
                reused_completed_simulation=reuse, failed=failed, accepted=accepted, seconds=round(time.monotonic()-start, 3)))
            save()
            print(sim, "PASS" if accepted else "FAIL", flush=True)
            assert accepted, f"{sim} combined regression failed"
            records = [json.loads(s) for s in (path/"records/cases.jsonl").read_text().splitlines()]
            assert len(records) == 1052
            assert sum(r["accepted"] for r in records) == 1048
            assert records == reference, "SPI records differ from the qualified compact10 expectations"
            pair.append(records)
        assert pair[0] == pair[1], "simulators disagree on SPI records"
        assert hashes == {p.relative_to(ROOT).as_posix(): digest(p) for p in inputs}, "source drift"
        assert source_hashes == {p.name: digest(p) for p in src.glob("*.v")}
        result.update(status="PASS_LEGACY_PUBLIC_MATRIX", spi_records_per_simulator=1052,
                      expected_spi_input_hold_negatives=4, cross_simulator_identical=True,
                      limitations="UART host service and SPI held-input premises unchanged; I2C and physical evidence are separate gates")
    except Exception as error:
        result.update(status="FAILED_OR_INCOMPLETE", error=str(error))
        raise
    finally:
        save()


if __name__ == "__main__":
    main()
