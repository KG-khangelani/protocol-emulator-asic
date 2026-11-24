# SPDX-License-Identifier: Apache-2.0
"""Replay the 1,160 original I2C cases with the selected-project handoff."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from run import (G4, ROOT, archive_member, digest, fresh_output, library_hashes, now,
                 read_json, replace_once, require, verify)


def setup_fixture(out, previous):
    fixture = out / "fixture"
    fixture.mkdir()
    for name in ("Makefile", "tb.v"):
        source = previous / "fixture" / name
        require(digest(source.read_bytes()) == read_json(previous / "result.json")["fixture_sha256"][name],
                "original high-enable fixture " + name)
        shutil.copyfile(source, fixture / name)
    text = (ROOT / "test/test_i2c_general_public.py").read_text(encoding="utf-8")
    text = replace_once(text, "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))", """
from importlib.util import module_from_spec, spec_from_file_location
root = Path(os.environ['COUNCIL_ROOT'])
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / 'test'))
spec = spec_from_file_location('test', root / 'test/test.py')
helper = module_from_spec(spec)
sys.modules['test'] = helper
spec.loader.exec_module(helper)
""")
    text = replace_once(text, "await edge(dut, rst_n=0, ena=0)", "await edge(dut, rst_n=0, ena=1)")
    old = """    dut.ui_in.value = 0
    dut.uio_in.value = 3
    await edge(dut, ena=0)
    await edge(dut, ena=0)"""
    new = """    dut.ui_in.value = 0xE7
    dut.uio_in.value = 3
    for _ in range(2):
        await edge(dut, ena=1)
        assert int(dut.uio_oe.value) == 0 and int(dut.uo_out.value) == 0x20
    await Timer(1, unit='ns')
    assert int(dut.clk.value) == 0
    dut.ui_in.value = 0x67
    await Timer(2, unit='ns')
    assert int(dut.uio_oe.value) == 0 and int(dut.uo_out.value) == 0x22
    dut.ui_in.value = 0
    await Timer(2, unit='ns')
    assert int(dut.uio_oe.value) == 0 and int(dut.uo_out.value) == 0x20"""
    (fixture / "council_i2c_matrix.py").write_bytes(replace_once(text, old, new).encode())
    return fixture


def execute(out, previous, pdk, result):
    identity = verify(ROOT)
    reference = read_json(previous / "result.json")
    require(reference["status"] == "pass", "first complete G3 screen is required")
    net_sha = digest((previous / "submitted.v").read_bytes())
    require(net_sha == reference["netlist_sha256"] == read_json(G4 / "ci-43543626249/result.json")["netlist_sha256"],
            "submitted netlist identity")
    for name, sha in identity["model_sha256"].items():
        require(digest((previous / "models" / name).read_bytes()) == sha, name)
    for rel, sha in library_hashes().items():
        require(digest((pdk / rel).read_bytes()) == sha, rel)
    fixture = setup_fixture(out, previous)
    result["netlist_sha256"] = net_sha
    result["testbench_sha256"] = {p.name: digest(p.read_bytes()) for p in fixture.iterdir()}
    results = out / "records"
    env = dict(os.environ, COUNCIL_ROOT=str(ROOT), G2_CURRENT="yes", G2_SRAM="yes",
               PDK_ROOT=str(pdk), SRAM_MODEL_DIR=str(previous / "models"),
               I2C_GENERAL_SMOKE="0", I2C_GENERAL_VARIANT="od128", I2C_GENERAL_RECORD_DIR=str(results),
               COCOTB_RANDOM_SEED="20261112", PYTHONHASHSEED="0",
               PYTHONPATH=os.pathsep.join(map(str, (fixture, ROOT / "test", ROOT))))
    cmd = ["make", "-C", str(fixture), "SIM=icarus", "GATES=yes", "SRC_DIR=" + str(ROOT / "src"),
           "GATE_LEVEL_NETLIST=" + str(previous / "submitted.v"), "SIM_BUILD=" + str(out / "sim"),
           "COCOTB_TEST_MODULES=council_i2c_matrix", "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
           "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
    result["command"] = cmd
    with (out / "run.log").open("wb") as log:
        status = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=5400).returncode
    require(status == 0, "make failed, see run.log")
    tests = ET.parse(out / "results.xml").findall(".//testcase")
    require(len(tests) == 1 and tests[0].get("name") == "complete_i2c_transactions" and not list(tests[0]),
            "complete matrix did not pass")
    source = archive_member(G4 / "ci-43543626249", 14096124429, "output/i2c/cases.jsonl")
    output = (results / "cases.jsonl").read_bytes()
    original = [json.loads(line) for line in source.splitlines()]
    observed = [json.loads(line) for line in output.splitlines()]
    require(len(original) == len(observed) == 1160, "matrix incomplete")
    index = {row["name"]: row for row in observed}
    require(len(index) == 1160, "case identity duplicated")
    result["differences"] = [row["name"] for row in original if index.get(row["name"]) != row]
    result["retained_records_sha256"] = digest(source)
    result["new_records_sha256"] = digest(output)
    result["expected_rejections"] = sum(not row["expected_acceptance"] for row in observed)
    result["terminal_outcomes"] = dict(Counter(str(row["outcome"]) for row in observed))
    require(not result["differences"], "case records differ")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--g3", required=True, type=Path)
    parser.add_argument("--pdk", required=True, type=Path)
    args = parser.parse_args()
    out = fresh_output(args.out)
    result = {"started_utc": now(), "status": "incomplete",
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "driver_sha256": digest(Path(__file__).read_bytes())}
    try:
        execute(out, args.g3.resolve(), args.pdk.resolve(), result)
        result["status"] = "pass"
    except Exception as err:
        result["error"] = str(err)
        raise
    finally:
        result["ended_utc"] = now()
        cases = out / "records/cases.jsonl"
        result["completed_records"] = len(cases.read_bytes().splitlines()) if cases.is_file() else 0
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["status"], result["completed_records"], out, flush=True)


if __name__ == "__main__":
    main()
