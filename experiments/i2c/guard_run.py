# SPDX-License-Identifier: Apache-2.0
"""Run one complete I²C guard comparison in the locked Linux workbench."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from guard_cases import ROOT, cases, digest, encoded
sys.path.insert(0, str(ROOT/"evidence/E0049-review-council/panel-c"))
from selector_orders import ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES, checked
from tools.cold_load import FIXTURE, fresh_directory, prepare_models
from tools.production_sram import verify
from tools.run_program_examples import run as execute


def stamp():
    return datetime.now(timezone.utc).isoformat()


def run(out, backend, models_root, smoke):
    out = fresh_directory(out)
    report = dict(backend=backend,smoke=smoke,started_utc=stamp(),status="INCOMPLETE")
    try:
        profile = verify(ROOT)
        models = prepare_models(out,profile)
        report["profile_sha256"] = profile["profile_sha256"]
        netlist = pdk = None
        if backend == "netlist":
            archive = ROOT/ARCHIVE
            checked(archive.read_bytes(),ARCHIVE_SHA,"G4 archive")
            netlist = out/"submitted.v"
            with ZipFile(archive) as z:
                netlist.write_bytes(checked(z.read("tt_submission/tt_um_khangelani_protocol_emulator.v"),NETLIST_SHA,"G4 netlist"))
            pdk = out/"pdk"
            for rel, sha in PDK_FILES.items():
                path = pdk/"ihp-sg13cmos5l/libs.ref"/rel
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(checked((models_root/rel).read_bytes(),sha,rel))
            report.update(netlist_sha256=NETLIST_SHA,cell_models=PDK_FILES)
        simulator = "verilator" if backend=="verilator" else "icarus"
        fixture = out/"fixture"
        fixture.mkdir()
        shutil.copyfile(FIXTURE/"tb.v",fixture/"tb.v")
        shutil.copyfile(Path(__file__).with_name("guard_suite.py"),fixture/"guard_suite.py")
        command = ["make","-C",str(fixture),"-f",str(ROOT/"test/Makefile"),"SIM="+simulator,
                   "SRC_DIR="+str(ROOT/"src"),"SIM_BUILD="+str(out/"sim"),"COCOTB_TEST_MODULES=guard_suite",
                   "COCOTB_RESULTS_FILE="+str(out/"results.xml"),"FST=","COCOTB_PLUSARGS=+NO_DUMP"]
        if netlist:
            command.extend(("GATES=yes","GATE_LEVEL_NETLIST="+str(netlist),"PDK_ROOT="+str(pdk)))
        env = dict(os.environ, I2C_GUARD_OUT=str(out), I2C_GUARD_ROOT=str(ROOT), I2C_GUARD_SMOKE=str(int(smoke)),
                   GENERAL_IO="yes",G2_CURRENT="yes",G2_SRAM="yes",SRAM_MODEL_DIR=str(models),
                   COCOTB_RANDOM_SEED="20261125",PYTHONHASHSEED="0")
        execute(command,out,"simulator",7200,env)
        executed = ET.parse(out/"results.xml").findall(".//testcase")
        if len(executed)!=1 or executed[0].get("name")!="compare_guards" or list(executed[0]):
            raise RuntimeError("cocotb did not report one passing guard comparison")
        rows = list(map(json.loads,(out/"cases.jsonl").read_bytes().splitlines()))
        if len(rows)!=(7 if smoke else len(list(cases()))) or not all(r["expectation_matched"] for r in rows):
            raise RuntimeError("incomplete or rejected case inventory")
        report.update(status="PASS",command=command,cases=len(rows),case_log_sha256=digest((out/"cases.jsonl").read_bytes()),
                      traces_sha256=digest((out/"traces.jsonl.gz").read_bytes()))
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        report["ended_utc"] = stamp()
        (out/"result.json").write_bytes(encoded(report))
        print(report["status"], backend, out, flush=True)


if __name__=="__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("backend",choices=("icarus","verilator","netlist"))
    p.add_argument("out",type=Path)
    p.add_argument("--pdk-models",type=Path,help="directory containing the three pinned functional model paths")
    p.add_argument("--smoke",action="store_true")
    args=p.parse_args()
    if args.backend=="netlist" and not args.pdk_models:
        p.error("--pdk-models is required for the netlist")
    run(args.out,args.backend,args.pdk_models,args.smoke)
