# SPDX-License-Identifier: Apache-2.0
"""Bounded existing-instruction phase-1 capacity screen, not an ISA lower bound."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import monotonic
import xml.etree.ElementTree as ET
from build_variants import ROOT, FILES, build
from run_formal import digest
from run_program_sensitivity import execute
sys.path.insert(0,str(ROOT))
from experiments.spi_phase.phase1_capacity import search, best_reference, evaluate
from experiments.spi_phase.four_mode_programs import describe


def reference_sweep(out, seconds=180):
    start=monotonic()
    count=0
    witnesses=[]
    for mode in (1,3):
        for order in (0,1):
            program=best_reference(mode,order)
            for profile,responses in (("late",[96]*8),("early",[1]*8),
                                      ("mixed",[1,96,2,95,48,24,72,12])):
                for rx in range(256):
                    if monotonic()-start>seconds:
                        raise TimeoutError("fixed reference-sweep budget exceeded")
                    record,trace=evaluate(program,mode,order,rx=rx,tx=(73*rx+19)&255,
                                          responses=responses)
                    if not record["accepted"]:
                        raise AssertionError(record)
                    count+=1
                    if rx==0x69:
                        witnesses.append({"case":record,"response_profile":profile,"trace":trace})
            record,trace=evaluate(program,mode,order,profile="edge_only")
            assert not record["accepted"] and record["error_kinds"]==["received_byte"]
            assert record["commits"]==[[record["schedule"]["sample"][-1]+24,0x96]]
            witnesses.append({"case":record,"response_profile":"edge_only","trace":trace})
    (out/"reference-witnesses.json").write_text(json.dumps(witnesses,separators=(",",":"))+"\n")
    return {"positive_paired_byte_cases":count,"edge_only_controls":4,
            "all_tx_rx_pairs":False,"rtl_execution":"NOT_EVALUATED",
            "seconds":round(monotonic()-start,3),"wall_limit":seconds}


def simulations(out):
    sources=build(out/"variants")
    results=[]
    for simulator in ("icarus","verilator"):
        path=out/simulator;path.mkdir()
        env=dict(os.environ)
        for key in ("COCOTB_TEST_FILTER","COCOTB_TESTCASE","GATES","MAKEFLAGS"):
            env.pop(key,None)
        env["SPI_PHASE1_RECORD_DIR"]=str(path/"records")
        command=["make","-C","test","SIM="+simulator,
                 "SRC_DIR="+str(out/"variants/compact/src"),
                 "COCOTB_TEST_MODULES=test_spi_phase1_public","COCOTB_TEST_FILTER=",
                 "SIM_BUILD="+str(path/"sim"),"COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                 "FST=","COCOTB_PLUSARGS=+NO_DUMP"]
        run=execute(command,path/"run.log",180,env)
        cases=list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
        bad=[c.get("name") for c in cases if any(c.find(k) is not None for k in ("failure","error","skipped"))]
        records=[json.loads(line) for line in (path/"records/cases.jsonl").read_text().splitlines()] if (path/"records/cases.jsonl").exists() else []
        deletions=[r for r in records if r["kind"]=="EIGHT_WORD_DELETION"]
        capacity=[r for r in records if r["kind"]=="CAPACITY_REJECTION"]
        ok=(run["returncode"]==0 and len(cases)==1 and not bad and len(records)==112
            and len(deletions)==108 and len(capacity)==4
            and all(not r["accepted"] and r["expected_rejection"] for r in records)
            and all(r["all_observations_match_reference"] for r in deletions))
        results.append({"simulator":simulator,**run,"accepted":ok,
                        "tests":len(cases),"failed_or_skipped":bad,"records":records,
                        "records_sha256":{p.name:digest(p) for p in (path/"records").glob("*")}})
        (out/"simulation-progress.json").write_text(json.dumps(results,indent=2)+"\n")
        print(simulator,"PASS" if ok else "FAIL",flush=True)
        if not ok:
            raise RuntimeError(simulator+" public deletion/capacity screen failed")
    return sources,results,results[0]["records_sha256"]==results[1]["records_sha256"]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build/ output directory required")
    out.mkdir(parents=True)
    paths=[ROOT/"src"/n for n in FILES]
    paths += [ROOT/p for p in (
        "experiments/spi_phase/build_variants.py","experiments/spi_phase/run_formal.py",
        "experiments/spi_phase/run_program_sensitivity.py",
        "experiments/spi_phase/run_phase1_capacity.py","experiments/spi_phase/phase1_capacity.py",
        "experiments/spi_phase/four_mode_programs.py","experiments/spi_phase/phase_programs.py",
        "tools/spi_four_mode_oracle.py","tools/m1_contract_model.py",
        "tools/spi_phase_reference.py","tools/spi_mode0_oracle.py",
        "test/test_spi_phase1_capacity.py","test/test_spi_phase1_public.py",
        "test/test_spi_four_mode.py","test/test.py","test/Makefile","test/tb.v",
        "docs/specs/spi-phase1-capacity-screen.md","tools/workbench/toolchain.lock.json")]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    result={"status":"RUNNING","started_utc":datetime.now(timezone.utc).isoformat(),
            "scope":"DECLARED_PHASE1_SCHEDULE_FAMILY_AND_PUBLIC_REJECTION_CONTROLS",
            "input_sha256":hashes,"production_and_candidate_rtl":"UNCHANGED",
            "physical":"NOT_EVALUATED","global_minimum_or_impossibility_proved":False}
    def save(): (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        result["boundary_tests"]=execute(
            ["python3","-m","unittest","discover","-s","test","-p","test_spi_phase1_capacity.py"],
            out/"boundary-tests.log",60)
        assert result["boundary_tests"]["returncode"]==0
        result["search"]=search()
        save()
        print("Family search:",result["search"]["family_minimum_words"],flush=True)
        if any(n<=8 for n in result["search"]["family_minimum_words"].values()):
            result["status"]="FITTING_CANDIDATE_REQUIRES_NEW_QUALIFICATION"
            return 1
        result["reference"]=reference_sweep(out)
        save()
        print("Reference sweep:",result["reference"]["positive_paired_byte_cases"],"PASS",flush=True)
        result["sources"],result["simulations"],result["cross_simulator_records_identical"]=simulations(out)
        assert result["cross_simulator_records_identical"]
        assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in paths},"source drift"
        result["status"]="PASS_DECLARED_PHASE1_CAPACITY_SCREEN"
    except TimeoutError as error:
        result.update(status="INCONCLUSIVE_TIMEOUT",error=str(error));raise
    except Exception as error:
        result.update(status="HARNESS_OR_CHECK_FAILURE",error=str(error));raise
    finally:
        save();print(out,flush=True)
    return 0 if result["status"]=="PASS_DECLARED_PHASE1_CAPACITY_SCREEN" else 1


if __name__=="__main__":
    raise SystemExit(main())
