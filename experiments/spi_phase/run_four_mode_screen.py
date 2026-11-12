# SPDX-License-Identifier: Apache-2.0
"""Four-mode reference feasibility plus scoped fitting-image public RTL checks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from experiments.spi_phase.four_mode_programs import image,execute_reference,describe
from tools.spi_four_mode_oracle import timing,raw_at,assess
from build_variants import build,FILES
from legacy_baseline import baseline_inputs
from run_program_sensitivity import execute


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def evaluate(mode,order,family,profile,rx=0x69,responses=None):
    tx=(73*rx+19)&255
    program,cs=image(mode,order,family)
    schedule=timing(mode,cs)
    cache={n:raw_at(n,schedule,rx,order,profile,responses) for n in range(-1,schedule["halt"]+1)}
    trace,commits=execute_reference(program,tx=tx,raw=cache.__getitem__,steps=schedule["halt"])
    captures=[s+(24 if family=="held" else 2) for s in schedule["sample"]]
    errors=assess(trace,schedule,tx,rx,order,captures)
    wanted=(family=="exact" or (family=="held" and profile=="held") or
            (family=="naive" and mode==0))
    if (not errors)!=wanted:
        raise AssertionError((mode,order,family,profile,rx,errors[:3]))
    if family=="held" and profile=="edge_only":
        assert commits==[[captures[-1],rx^255]]
        assert {e["kind"] for e in errors}=={"received_byte"}
    if family=="naive" and mode==2:
        assert commits==[[379,rx]]
        assert errors==[{"kind":"idle_before_cs","edge":1}]
    selected={0,1,cs-1,cs,*schedule["leading"],*schedule["trailing"],*captures,schedule["release"],schedule["halt"]}
    record={"mode":mode,"order":order,"family":family,"profile":profile,"rx":rx,"tx":tx,
            **describe(program),"schedule_pass":not errors,"expected_acceptance":wanted,
            "commits":commits,"error_kinds":sorted({e["kind"] for e in errors}),
            "first_errors":errors[:4],"schedule":schedule}
    return record,[r for r in trace if r["edge"] in selected]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build/ output required")
    out.mkdir(parents=True)
    paths=baseline_inputs()
    paths += [ROOT/p for p in (
        "tools/spi_four_mode_oracle.py","tools/m1_contract_model.py","tools/spi_mode0_oracle.py",
        "tools/spi_phase_reference.py","experiments/spi_phase/phase_programs.py",
        "experiments/spi_phase/four_mode_programs.py","experiments/spi_phase/run_four_mode_screen.py",
        "experiments/spi_phase/build_variants.py","experiments/spi_phase/run_program_sensitivity.py",
        "test/test_spi_four_mode.py","test/test_spi_four_mode_public.py","test/test.py",
        "test/Makefile","test/tb.v","docs/specs/p-spi-host-4mode.md")]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    result={"status":"RUNNING","scope":"REFERENCE_SCHEDULE_SCREEN_AND_SCOPED_PUBLIC_RTL",
            "started_utc":datetime.now(timezone.utc).isoformat(),"input_sha256":hashes,
            "model_reference_capacity":16,"actual_compact_capacity":8,
            "production_and_candidate_rtl":"UNCHANGED","simulations":[]}
    def save(): (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        unit=execute(["python3","-m","unittest","discover","-s","test","-p","test_spi_four_mode.py"],
                     out/"oracle-tests.log",60)
        result["oracle_tests"]=unit; save()
        if unit["returncode"]: raise RuntimeError("oracle boundary tests failed")
        count=0; witnesses=[]
        for family,profiles in (("exact",("held","edge_only")),("held",("held",))):
            for mode in range(4):
                for order in (0,1):
                    for profile in profiles:
                        for rx in range(256):
                            record,trace=evaluate(mode,order,family,profile,rx)
                            count+=1
                            if rx==0x69: witnesses.append({"case":record,"trace":trace})
                    for responses in ([1]*8,[1,96,2,95,48,24,72,12]):
                        evaluate(mode,order,family,"held",responses=responses)
                        count+=1
        controls=[]
        for family,profile in (("held","edge_only"),("naive","held")):
            for mode in range(4):
                for order in (0,1):
                    record,trace=evaluate(mode,order,family,profile)
                    controls.append(record); witnesses.append({"case":record,"trace":trace})
        assert count==6176 and len(controls)==16
        result["reference"]={"positive_cases":count,"control_cases":controls,
            "limited_family_search":True,"minimum_or_impossibility_proved":False}
        (out/"reference-witnesses.json").write_text(json.dumps(witnesses,indent=2)+"\n")
        save(); print("reference",count,"positive cases and 16 controls PASS",flush=True)
        result["sources"]=build(out/"variants")
        for sim in ("icarus","verilator"):
            path=out/sim; path.mkdir()
            env=dict(os.environ)
            for k in ("COCOTB_TEST_FILTER","COCOTB_TESTCASE","GATES","MAKEFLAGS"): env.pop(k,None)
            env["SPI_FOUR_MODE_RECORD_DIR"]=str(path/"records")
            command=["make","-C","test","SIM="+sim,"SRC_DIR="+str(out/"variants/compact/src"),
                     "COCOTB_TEST_MODULES=test_spi_four_mode_public","COCOTB_TEST_FILTER=",
                     "SIM_BUILD="+str(path/"sim"),"COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                     "FST=","COCOTB_PLUSARGS=+NO_DUMP"]
            run=execute(command,path/"run.log",180,env)
            cases=list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
            bad=[c.get("name") for c in cases if any(c.find(k) is not None for k in ("failure","error","skipped"))]
            records=[json.loads(x) for x in (path/"records/cases.jsonl").read_text().splitlines()] if (path/"records/cases.jsonl").exists() else []
            ok=run["returncode"]==0 and len(cases)==1 and not bad and len(records)==36
            ok=ok and sum(r["accepted"] for r in records)==26
            ok=ok and all(r["accepted"]==r["expected_acceptance"] for r in records)
            result["simulations"].append({"simulator":sim,**run,"accepted":ok,"tests":len(cases),
                "failed_or_skipped":bad,"records":records,
                "records_sha256":{p.name:digest(p) for p in (path/"records").glob("*")}})
            save(); print(sim,"PASS" if ok else "FAIL",flush=True)
            if not ok: raise RuntimeError(sim+" public screen failed")
        result["cross_simulator_records_identical"]=result["simulations"][0]["records_sha256"]==result["simulations"][1]["records_sha256"]
        assert result["cross_simulator_records_identical"]
        assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in paths},"source drift"
        result["status"]="PASS_SCOPED_SCREEN"
    except Exception as error:
        result.update(status="FAIL",error=str(error)); raise
    finally:
        save(); print(out,flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
