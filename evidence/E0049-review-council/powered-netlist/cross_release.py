# SPDX-License-Identifier: Apache-2.0
"""Compare both published software milestones with a permanently selected host."""
import argparse
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from run import (ROOT, G4, GROUPS, archive_member, audit_records, build, digest, fresh_output,
                 library_hashes, now, read_json, replace_once, require, stage_fixture, verify)
from experiments.waveform_replay.run import build as build_waveforms

G5 = ROOT / "evidence/E0048-waveform-replay/ci-66743b6"
WAVE_GROUPS = {"replay_loader", "replay_waveforms", "replay_falsification"}


def prepare_waveform_suite(fixture):
    src = (ROOT / "test/test_waveform_replay_public.py").read_text()
    src = replace_once(src, "Path(__file__).resolve().parents[1]", "Path(os.environ['COUNCIL_ROOT'])")
    src = replace_once(src, "from test import edge, initialise",
                       "import council_powered_g3\nfrom test import edge, initialise")
    selection = """assert [c['name'] for c in CONTRACT['cases'] if c.get('pause_edges')] == ['paused-wall-clock']
CONTRACT['cases'] = [c for c in CONTRACT['cases'] if not c.get('pause_edges')]
assert len(CONTRACT['cases']) == 20
"""
    src = replace_once(src, "BUILT = Path", selection + "BUILT = Path")
    src = replace_once(src, "dut.ui_in.value = step['ui_in']",
                       "selector = 0xE7 if step['action'] == 'flush_idle' else step['ui_in']\n"
                       "        dut.ui_in.value = selector")
    src = replace_once(src, "ena=step['ena']", "ena=1")
    src = replace_once(src, "'ui_in': step['ui_in'], 'rst_n': step['rst_n'], 'ena': step['ena']",
                       "'ui_in': selector, 'rst_n': step['rst_n'], 'ena': 1")
    handoff = """assert write_index == 80
    await Timer(1, unit='ns')
    assert int(dut.clk.value) == 0
    dut.ui_in.value = 0x67
    await Timer(2, unit='ns')
    assert int(dut.uo_out.value) == 0x22 and int(dut.uio_oe.value) == 0
    dut.ui_in.value = 0
    await Timer(2, unit='ns')
    assert int(dut.uo_out.value) == 0x20 and int(dut.uio_oe.value) == 0"""
    src = replace_once(src, "assert write_index == 80", handoff)
    (fixture / "council_powered_g5.py").write_bytes(src.encode())


def compare_g5(directory):
    archive = G5 / "14155007514.zip"
    identity = next(row["digest"] for row in read_json(G5 / "artifacts.json")["artifacts"]
                    if row["id"] == 14155007514)
    require("sha256:" + digest(archive.read_bytes()) == identity, "G5 original ZIP identity")
    ours = {r["name"]: r for r in map(json.loads, (directory / "records.jsonl").read_bytes().splitlines())}
    rows = []
    with zipfile.ZipFile(archive) as z:
        prefix = "primary/icarus/records/"
        theirs = {r["name"]: r for r in map(json.loads, z.read(prefix + "records.jsonl").splitlines())}
        require(len(theirs) == 21 and set(theirs)-set(ours) == {"paused-wall-clock"} and len(ours) == 20,
                "complete board-applicable G5 case set")
        for name, record in sorted(ours.items()):
            stored = theirs[name]
            fields = set(stored) | set(record)
            require(all(record.get(k) == stored.get(k) for k in fields - {"trace_sha256"}), name + " case verdict")
            theirs_raw = gzip.decompress(z.read(prefix + name + ".json.gz"))
            our_raw = gzip.decompress((directory / (name + ".json.gz")).read_bytes())
            require(digest(theirs_raw) == stored["trace_sha256"] and digest(our_raw) == record["trace_sha256"],
                    name + " trace record integrity")
            old, new = map(json.loads, (theirs_raw, our_raw))
            for load in old["loader"]:
                load["ena"] = 1
                if load["action"] == "flush_idle":
                    load["ui_in"] = 0xE7
            require(old == new, name + " complete projected loader and runtime rows")
            rows.append({"name": name, "accepted": record["accepted"], "binary": record["binary_sha256"],
                         "loader_edges": len(new["loader"]), "runtime_rows": len(new["runtime"]),
                         "trace_sha256": record["trace_sha256"]})
    return {"compared": rows, "cases": len(rows), "expected_rejections": sum(not r["accepted"] for r in rows),
            "excluded_macro_enable_case": "paused-wall-clock", "archive_digest": identity}


def simulate(out, mode, g3_netlist, pdk, result):
    guard = verify(ROOT)
    models = g3_netlist / "models"
    require(all(digest((models / name).read_bytes()) == expected for name, expected in guard["model_sha256"].items()),
            "functional SRAM models")
    fixture = stage_fixture(out)
    prepare_waveform_suite(fixture)
    result["fixture_sha256"] = {p.name: digest(p.read_bytes()) for p in fixture.iterdir()}
    build(out / "g3-images")
    build_waveforms(out / "g5-images")
    env = dict(os.environ, COUNCIL_ROOT=str(ROOT), GENERAL_IO="yes", G2_CURRENT="yes", G2_SRAM="yes",
               SRAM_MODEL_DIR=str(models), G3_PROGRAM_BUILD=str(out/"g3-images"), G5_PROGRAM_BUILD=str(out/"g5-images"),
               G3_PROGRAM_RECORDS=str(out/"g3-records"), G5_RECORDS=str(out/"g5-records"),
               COCOTB_RANDOM_SEED="20261124", PYTHONHASHSEED="0",
               PYTHONPATH=os.pathsep.join(map(str, (fixture, ROOT/"test", ROOT))))
    selection = ["council_powered_g5"]
    extra = []
    if mode == "verilator":
        selection.insert(0, "council_powered_g3")
    else:
        pins = library_hashes()
        require(all(digest((pdk/rel).read_bytes()) == value for rel, value in pins.items()), "PDK identity")
        net = g3_netlist/"submitted.v"
        result["netlist_sha256"] = digest(net.read_bytes())
        require(all(read_json(G4/f"ci-{n}/result.json")["netlist_sha256"] == result["netlist_sha256"]
                    for n in (43543626249,43543629839)), "submitted netlist identity")
        extra = ["GATES=yes", "GATE_LEVEL_NETLIST=" + str(net)]
        env["PDK_ROOT"] = str(pdk)
    cmd = ["make", "-C", str(fixture), "SIM=" + mode, "SRC_DIR=" + str(ROOT/"src"), "SIM_BUILD=" + str(out/"sim"),
           "COCOTB_TEST_MODULES=" + ",".join(selection), "COCOTB_RESULTS_FILE=" + str(out/"results.xml"),
           "FST=", "COCOTB_PLUSARGS=+NO_DUMP", *extra]
    result["command"] = cmd
    with (out/"run.log").open("wb") as log:
        proc = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1000)
    require(proc.returncode == 0, "simulation returned " + str(proc.returncode))
    tests = ET.parse(out/"results.xml").findall(".//testcase")
    names = {t.get("name") for t in tests}
    require(names == (WAVE_GROUPS | GROUPS if mode == "verilator" else WAVE_GROUPS)
            and len(tests) == len(names) and all(not list(t) for t in tests), "all JUnit tests executed")
    result["testcases"] = sorted(names)
    result["g5"] = compare_g5(out/"g5-records")
    if mode == "verilator":
        actual = audit_records(out/"g3-records")
        ref = archive_member(G4/"program-tools",14094030144,"verilator/records/records.jsonl")
        require(actual == sorted(map(json.loads, ref.splitlines()), key=lambda r: r["name"]), "G3 case identity")
        require(len(actual) == 55, "G3 case count")
        result["g3"] = {"cases": len(actual), "reference_records_sha256": digest(ref),
                        "expected_rejections": sum(not r["expected_acceptance"] for r in actual),
                        "observations": sum(r["observations"] for r in actual)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("verilator","icarus"))
    parser.add_argument("out", type=Path)
    parser.add_argument("--g3-netlist", required=True, type=Path)
    parser.add_argument("--pdk", type=Path)
    args = parser.parse_args()
    require(args.mode == "verilator" or args.pdk, "Icarus stage requires --pdk")
    out = fresh_output(args.out)
    result = {"mode": args.mode, "started_utc": now(), "status": "incomplete"}
    try:
        simulate(out, args.mode, args.g3_netlist.resolve(), args.pdk and args.pdk.resolve(), result)
        result["status"] = "pass"
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        result["ended_utc"] = now()
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
        print(result["status"], out, flush=True)


if __name__ == "__main__":
    sys.exit(main())
