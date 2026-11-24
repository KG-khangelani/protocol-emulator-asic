# SPDX-License-Identifier: Apache-2.0
"""Compare a powered launch on the actual G4 netlist with the frozen G3 records."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
from tools.program_examples import build
from tools.production_sram import verify
from tools.run_program_examples import GROUPS, audit_records

G4 = ROOT / "evidence/E0047-g4-submission-candidate"
E43 = ROOT / "evidence/E0043-sram-physical-integration/guarded-netlist"
PDK = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def now():
    return datetime.now(timezone.utc).isoformat()


def fresh_output(path):
    path = path.resolve()
    require(path.is_relative_to(ROOT / "build"), "output must be under build/")
    path.mkdir(parents=True, exist_ok=False)
    return path


def library_hashes():
    evidence = read_json(E43 / "archive.json")
    archive = E43 / "netlist.tar.gz"
    require(digest(archive.read_bytes()) == evidence["sha256"], "G2 model provenance archive")
    with tarfile.open(archive) as packed:
        member = "icarus/result.json"
        raw = packed.extractfile(member).read()
    require(digest(raw) == evidence["files"][member], "G2 model provenance member")
    return {path.split(PDK + "/")[1]: value
            for path, value in json.loads(raw)["library_sha256"].items()}


def fetch_pdk(out):
    pins = library_hashes()
    require(len(pins) == 3, "pinned library set")
    for rel, expected in pins.items():
        url = f"https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/{rel}"
        with urlopen(Request(url, headers={"User-Agent": "asic-council-reproduction"}), timeout=30) as response:
            raw = response.read(500_000)
        require(digest(raw) == expected, "upstream library digest " + rel)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    print(f"Verified {len(pins)} PDK Verilog files at {PDK}")


def archive_member(directory, archive_id, member):
    info = next(r for r in read_json(directory / "artifacts.json")["artifacts"]
                if r["id"] == archive_id)
    path = directory / (str(archive_id) + ".zip")
    require("sha256:" + digest(path.read_bytes()) == info["digest"], "original archive " + str(archive_id))
    with zipfile.ZipFile(path) as z:
        return z.read(member)


def replace_once(text, old, new):
    require(text.count(old) == 1, "fixture edit did not match exactly once: " + old)
    return text.replace(old, new)


def stage_fixture(out):
    fixture = out / "fixture"
    fixture.mkdir()
    shutil.copyfile(ROOT / "test/Makefile", fixture / "Makefile")
    tb = (ROOT / "test/tb.v").read_text(encoding="utf-8")
    tb = replace_once(tb, ".ena    (ena),", ".ena    (1'b1),")
    monitor = """
  always @(posedge clk) begin
    if (ena !== 1'b1) $fatal(1, "host requested an unpowered edge");
  end
"""
    tb = replace_once(tb, "endmodule", monitor + "\nendmodule")
    (fixture / "tb.v").write_bytes(tb.encode())
    # Keep the G3 reference traces and every case assertion in the original suite.
    harness = (ROOT / "test/test_program_examples_public.py").read_text(encoding="utf-8")
    harness = replace_once(harness, "Path(__file__).resolve().parents[1]", "Path(os.environ['COUNCIL_ROOT'])")
    # The original suite runs from test/. Its helper has the same name as a
    # Python namespace package. Load that exact unedited helper in this fixture.
    imports = """sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'test'))
import importlib.util
helper_spec = importlib.util.spec_from_file_location('test', ROOT / 'test/test.py')
helper = importlib.util.module_from_spec(helper_spec)
sys.modules['test'] = helper
helper_spec.loader.exec_module(helper)"""
    harness = replace_once(harness, "sys.path.insert(0, str(ROOT))", imports)
    harness = replace_once(harness, "dut.ui_in.value = step['ui_in']",
                           "dut.ui_in.value = 0xE7 if step['action'] == 'flush_idle' else step['ui_in']")
    harness = replace_once(harness, "ena=step['ena']", "ena=1")
    handoff = """    await Timer(1, unit='ns')
    assert int(dut.clk.value) == 0 and plan['steps'][-1]['action'] == 'flush_idle'
    dut.ui_in.value = 0x67
    await Timer(2, unit='ns')
    assert int(dut.uo_out.value) == 0x22 and int(dut.uio_oe.value) == 0
    dut.ui_in.value = 0
    await Timer(2, unit='ns')
    assert int(dut.uo_out.value) == 0x20 and int(dut.uio_oe.value) == 0
    return observations"""
    harness = replace_once(harness, "    return observations", handoff)
    (fixture / "council_powered_g3.py").write_bytes(harness.encode())
    return fixture


def simulate(out, pdk, result):
    guard = verify(ROOT)
    pins = library_hashes()
    require(all(digest((pdk / rel).read_bytes()) == expected for rel, expected in pins.items()),
            "PDK model mismatch")
    result["pdk_sha256"] = pins
    candidate = G4 / "ci-43543626249"
    net = archive_member(candidate, 14094673928, "tt_submission/tt_um_khangelani_protocol_emulator.v")
    result["netlist_sha256"] = digest(net)
    for run_id in (43543626249, 43543629839):
        require(read_json(G4 / f"ci-{run_id}/result.json")["netlist_sha256"] == digest(net), "netlist identity")
    (out / "submitted.v").write_bytes(net)
    models = out / "models"
    models.mkdir()
    for name, expected in guard["model_sha256"].items():
        raw = gzip.decompress((ROOT / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" /
                               (name + ".gz")).read_bytes())
        require(digest(raw) == expected, "SRAM model identity")
        (models / name).write_bytes(raw)
    build(out / "examples")
    fixture = stage_fixture(out)
    result["fixture_sha256"] = {p.name: digest(p.read_bytes()) for p in fixture.iterdir() if p.is_file()}
    records_dir = out / "records"
    env = dict(os.environ, COUNCIL_ROOT=str(ROOT), G2_CURRENT="yes", G2_SRAM="yes",
               SRAM_MODEL_DIR=str(models), PDK_ROOT=str(pdk), G3_PROGRAM_BUILD=str(out / "examples"),
               G3_PROGRAM_RECORDS=str(records_dir), COCOTB_RANDOM_SEED="20261113", PYTHONHASHSEED="0",
               PYTHONPATH=os.pathsep.join(map(str, (fixture, ROOT / "test", ROOT))))
    cmd = ["make", "-C", str(fixture), "SIM=icarus", "GATES=yes", "SRC_DIR=" + str(ROOT / "src"),
           "GATE_LEVEL_NETLIST=" + str(out / "submitted.v"), "SIM_BUILD=" + str(out / "sim"),
           "COCOTB_TEST_MODULES=council_powered_g3", "COCOTB_RESULTS_FILE=" + str(out / "results.xml"),
           "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
    result["command"] = cmd
    with (out / "run.log").open("wb") as log:
        process = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
    result["returncode"] = process.returncode
    require(process.returncode == 0, "make returned failure; see run.log")
    tests = ET.parse(out / "results.xml").findall(".//testcase")
    require({t.get("name") for t in tests} == GROUPS and len(tests) == 4 and all(not list(t) for t in tests),
            "four executed passing groups required")
    actual = audit_records(records_dir)
    expected_bytes = archive_member(G4 / "program-tools", 14094030144, "icarus/records/records.jsonl")
    expected = sorted(map(json.loads, expected_bytes.splitlines()), key=lambda row: row["name"])
    require(len(actual) == len(expected) == 55, "expected 55 records")
    different = [a["name"] for a, b in zip(actual, expected) if a != b]
    result["reference_records_sha256"] = digest(expected_bytes)
    result["different_records"] = different
    result["cases"] = len(actual)
    result["expected_rejections"] = sum(not r["expected_acceptance"] for r in actual)
    result["tests"] = [t.get("name") for t in tests]
    result["observations"] = sum(r["observations"] for r in actual)
    require(not different, "normalized public records differ: " + str(different))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch-models", "run"])
    parser.add_argument("out", type=Path, help="new output directory under build/")
    parser.add_argument("--pdk", type=Path, help="root containing ihp-sg13cmos5l/")
    args = parser.parse_args()
    out = fresh_output(args.out)
    if args.action == "fetch-models":
        fetch_pdk(out)
        return
    require(args.pdk is not None, "specify --pdk for the simulation")
    result = {"started_utc": now(), "scope": "powered macro-pin launch, zero-delay G4 netlist",
              "source": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "driver_sha256": digest(Path(__file__).read_bytes()), "status": "incomplete"}
    try:
        simulate(out, args.pdk.resolve(), result)
        result["status"] = "pass"
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        result["ended_utc"] = now()
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(result["status"], out, flush=True)


if __name__ == "__main__":
    main()
