# SPDX-License-Identifier: Apache-2.0
"""Reproducible public comparison and whole-chip cost; formal is separate."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from build_variants import ROOT,FILES
from legacy_baseline import baseline_inputs
from build_timed_gpio import build
from run_formal import digest
from run_program_sensitivity import execute
from run_comparison import cell_counts,TOP
sys.path.insert(0,str(ROOT))
from experiments.spi_phase.timed_gpio_programs import evaluate,MIXED

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--smoke",action="store_true")
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build directory required")
    out.mkdir(parents=True)
    paths=baseline_inputs()+[ROOT/p for p in (
        "experiments/spi_phase/build_timed_gpio.py","experiments/spi_phase/timed_gpio_programs.py",
        "experiments/spi_phase/run_timed_gpio.py","experiments/spi_phase/build_variants.py",
        "experiments/spi_phase/phase_programs.py","experiments/spi_phase/four_mode_programs.py",
        "tools/m1_contract_model.py","tools/spi_four_mode_oracle.py","tools/spi_mode0_oracle.py",
        "tools/spi_phase_reference.py","test/test_spi_timed_gpio.py","test/test.py",
        "test/test_uart_rx_public.py","test/Makefile","test/tb.v",
        "docs/specs/spi-timed-gpio-comparison.md","tools/workbench/toolchain.lock.json")]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    result={"status":"RUNNING","started_utc":datetime.now(timezone.utc).isoformat(),"smoke_only":args.smoke,
            "input_sha256":hashes,"stages":[],"sources":build(out/"variants"),"measurements":{},
            "physical":"NOT_EVALUATED","formal":"SEPARATE_REQUIRED_GATE"}
    def save(): (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    def run(name,command,*,env=None,junit=None,count=None,failures=()):
        record={"name":name,**execute(command,out/(name+".log"),600,env)}
        ok=record["returncode"]==0
        if junit is not None:
            cases=list(ET.parse(junit).getroot().iter("testcase")) if junit.exists() else []
            failed=sorted(c.get("classname","")+"."+c.get("name","") for c in cases
                          if c.find("failure") is not None or c.find("error") is not None)
            skipped=[c.get("name") for c in cases if c.find("skipped") is not None]
            record.update(tests=len(cases),failed=failed,skipped=skipped)
            ok=(len(cases)==count and not skipped and failed==sorted(failures)
                and ((record["returncode"]!=0) if failures else record["returncode"]==0)
                and not record["timed_out"])
        record["accepted"]=ok;result["stages"].append(record);save()
        print(name,"PASS" if ok else "FAIL",flush=True)
        if not ok:raise RuntimeError(name+" failed")
    try:
        if not args.smoke:
            for variant in ("P","F"):
                total=0
                for mode in (1,3):
                    for order in (0,1):
                        for responses in ([1]*8,[96]*8,MIXED):
                            for rx in range(256):
                                _,_,errors=evaluate(variant,mode,order,(73*rx+19)&255,rx,responses)
                                assert not errors,errors[:4]
                                total+=1
                result.setdefault("reference",{})[variant]={"paired_byte_positives":total}
                save();print(variant,"reference",total,"PASS",flush=True)
        all_records={}
        for variant in ("compact8","compact10","P","F"):
            directory=out/variant;directory.mkdir()
            env=dict(os.environ)
            for key in ("COCOTB_TEST_FILTER","COCOTB_TESTCASE","GATES","MAKEFLAGS"):
                env.pop(key,None)
            def simulate(simulator,modules,label,count,failures=()):
                path=directory/label;path.mkdir()
                env["TIMED_GPIO_VARIANT"]=variant
                env["TIMED_GPIO_RECORD_DIR"]=str(path/"records")
                env["TIMED_GPIO_SMOKE"]=str(int(args.smoke))
                command=["make","-C","test","SIM="+simulator,
                    "SRC_DIR="+str(out/"variants"/variant/"src"),"COCOTB_TEST_MODULES="+modules,
                    "COCOTB_TEST_FILTER=","SIM_BUILD="+str(directory/"sim"/simulator),
                    "COCOTB_RESULTS_FILE="+str(path/"results.xml"),"FST=","COCOTB_PLUSARGS=+NO_DUMP"]
                run(variant+"-"+label,command,env=env,junit=path/"results.xml",count=count,failures=failures)
                return path
            if not args.smoke:
                failures=(["test.invalid_encoding_and_out_of_range_fail_closed"] if variant in ("P","F")
                          else ["test.invalid_length_never_releases_engine"] if variant=="compact10" else [])
                simulate("icarus","test,test_uart_rx_public","legacy",20,failures)
            if variant!="compact8":
                pair=[]
                for sim in ("icarus","verilator"):
                    path=simulate(sim,"test_spi_timed_gpio","public-"+sim,2)
                    records=[json.loads(s) for s in (path/"records/cases.jsonl").read_text().splitlines()]
                    transfers=[r for r in records if "trace_sha256" in r]
                    assert len(transfers)==(28 if args.smoke else 1052),len(transfers)
                    pair.append(records)
                    result.setdefault("public",{}).setdefault(variant,{})[sim]={
                        "cases":len(transfers),"positive":sum(r["accepted"] for r in transfers),
                        "expected_negative":sum(not r["accepted"] for r in transfers),
                        "records_sha256":digest(path/"records/cases.jsonl"),
                        "trace_files":{p.name:digest(p) for p in (path/"records").glob("*.json")}}
                    save()
                assert pair[0]==pair[1],"simulator record mismatch"
                all_records[variant]={r["name"]:r["contract_trace_sha256"] for r in pair[0]
                                      if "contract_trace_sha256" in r}
            if not args.smoke:
                src=out/"variants"/variant/"src"
                netlist=directory/"synth.json"
                script="read_verilog "+" ".join(str(src/n) for n in FILES)
                script+=f"; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {netlist}"
                run(variant+"-synthesis",["yosys","-Q","-p",script])
                result["measurements"][variant]=cell_counts(netlist);save()
        assert all_records["P"]==all_records["F"]==all_records["compact10"]
        result["cross_simulator_records_identical"]=True
        result["cross_variant_spi_contract_traces_identical"]=True
        assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in paths},"source drift"
        result["status"]="SMOKE_ONLY_NOT_QUALIFIED" if args.smoke else "PASS_PUBLIC_AND_GENERIC_COMPARISON_FORMAL_PENDING"
    except Exception as error:
        result.update(status="CHECK_OR_HARNESS_FAILURE",error=str(error));raise
    finally:save()
    return 0

if __name__=="__main__":raise SystemExit(main())
