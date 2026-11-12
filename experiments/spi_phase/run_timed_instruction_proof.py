# SPDX-License-Identifier: Apache-2.0
"""Timed instruction induction/refinement, covers, and validated negative controls."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
from build_variants import ROOT,FILES,once
from legacy_baseline import baseline_inputs
from build_timed_gpio import build
from run_formal import PORTS,DERIVED,INPUTS,digest,instrument,vector
from run_integration import readouts
from run_program_sensitivity import execute,vcd_frames

def prepare(out,variant):
    sources=build(out/"variants"); inputs=out/"inputs"; inputs.mkdir()
    extras={"formal_phase_active":1,"formal_phase_prepared":1}
    if variant=="F":extras.update(formal_gpio_pending=1,formal_gpio_pending_value=8,formal_gpio_pending_oe=8)
    engine=instrument((out/"variants"/variant/"src/m1_engine.v").read_text(encoding="utf-8"))
    if variant=="F":
        names={n:w for n,w in extras.items() if "gpio" in n}
        engine=readouts(engine,[
            ("output wire formal_phase_active, output wire formal_phase_prepared\n",
             "output wire formal_phase_active, output wire formal_phase_prepared, "+
             ", ".join("output wire "+(f"[{w-1}:0] " if w>1 else "")+n for n,w in names.items())+"\n"),
            ("    reg [7:0] gpio_pending_value, gpio_pending_oe;",
             "    reg [7:0] gpio_pending_value, gpio_pending_oe;\n"+
             "".join(f"    assign {n}={n.removeprefix('formal_')};\n" for n in names))
        ],"timed-readouts.v",inputs)
    (inputs/"phase_engine.v").write_text(engine)
    compact=instrument((out/"variants/compact8/src/m1_engine.v").read_text(encoding="utf-8"))
    (inputs/"compact_engine.v").write_text(once(compact,"module phase_engine #","module compact_engine #"))
    ports={**PORTS,**extras}
    def decl(prefix,selected=ports):
        return "".join("wire "+(f"[{w-1}:0] " if w>1 else "")+prefix+n+";\n" for n,w in selected.items())
    def inst(module,label,prefix,selected=ports):
        return module+" "+label+"("+",\n".join([f".{n}({n})" for n in INPUTS]+[f".{n}({prefix+n})" for n in selected])+");\n"
    states={n:w for n,w in ports.items() if n not in DERIVED}
    header=decl("")+inst("phase_engine","dut","")
    header+=vector("all_state",list(states),list(states.values()))
    latched={n:w for n,w in states.items() if n not in {"pc","state","wait_left"}}
    header+=vector("phase_latched_state",list(latched),list(latched.values()))
    phase={n:w for n,w in states.items() if (n.startswith("shift_") and n!="shift_period_status") or n.startswith("formal_phase_")}
    header+=vector("gpio_phase_state",list(phase),list(phase.values()))
    (inputs/"phase_bindings.vh").write_text(header)
    base={**PORTS,"formal_phase_active":1,"formal_phase_prepared":1}
    ref=decl("c_")+decl("l_",base)+inst("phase_engine","candidate","c_")+inst("compact_engine","compact","l_",base)
    ref+=vector("candidate_outputs",["c_"+n for n in base],list(base.values()))
    ref+=vector("compact_outputs",["l_"+n for n in base],list(base.values()))
    (inputs/"refinement_bindings.vh").write_text(ref)
    for name in ("timed_properties.sv","timed_gpio_properties.vh","timed_refinement.sv"):
        (inputs/name).write_bytes((ROOT/"experiments/spi_phase/formal"/name).read_bytes())
    return sources

def control_check(name,task):
    witnesses=list((task/"proof/engine_0").glob("trace*.vcd"))
    rows=[]
    for p in witnesses:
        # The shared parser only accepts the public_spi top scope. A retained
        # copy renames that scope, preserving every signal value and timestamp.
        normalized=task/("parsed-"+p.name)
        normalized.write_text(p.read_text(encoding="utf-8").replace("$scope module timed_properties $end","$scope module public_spi $end"))
        rows.extend(vcd_frames(normalized))
    rows=[r for r in rows if r.get("time",0)%10==0]
    observations=[]
    for a,b in zip(rows,rows[1:]):
        if not a.get("set_issue") or not a.get("gpio_delay"):continue
        if name=="wrong_count":
            if b.get("wait_left")==a["gpio_delay"]:observations.append({"issue_delay":a["gpio_delay"],"observed_count":b["wait_left"]})
        elif not a.get("gpio_before") and b.get("gpio_value")==a.get("set_value"):
            observations.append({"expected_gpio":a["set_value"],"observed_gpio":b["gpio_value"]})
    return {"validated":bool(observations),"observations":observations,
            "witness_sha256":{p.name:digest(p) for p in witnesses}}

def run_case(out,variant,name,mode,top,expected,defines):
    task=out/name;task.mkdir();inputs=out/"inputs"
    names=["phase_engine.v",top+".sv"]
    if top=="timed_refinement":names+=["compact_engine.v","refinement_bindings.vh"]
    else:names+=["phase_bindings.vh","timed_gpio_properties.vh"]
    flags=("-D VARIANT_F " if variant=="F" else "")+defines
    depth=12 if mode=="prove" else 80
    cfg=f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n"
    cfg+="read -formal -sv "+flags+" "+" ".join(n for n in names if not n.endswith(".vh"))+"\nprep -top "+top+"\n\n[files]\n"
    cfg+="\n".join(str(inputs/n) for n in names)+"\n"
    (task/"proof.sby").write_text(cfg)
    run=execute(["sby","-f","-d",str(task/"proof"),str(task/"proof.sby")],task/"proof.log",180)
    raw=(task/"proof/status").read_text().strip() if (task/"proof/status").exists() else "MISSING"
    match=re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}",raw);status=match[1] if match else "MISSING_OR_MALFORMED"
    log=(task/"proof.log").read_text()
    induction="successful proof by k-induction" in log
    failed=re.findall(r"Assert failed in (.+)",log)
    reached=re.findall(r"Reached cover statement in step (\d+) at (.+)",log)
    check=control_check(name,task) if expected=="FAIL" and status=="FAIL" else None
    ok=not run["timed_out"] and run["returncode"]==0 and status==expected
    if mode=="prove":ok=ok and induction
    if mode=="cover":ok=ok and len(reached)==(5 if variant=="F" else 4)
    if expected=="FAIL":ok=ok and bool(failed) and check["validated"]
    return {"name":name,"mode":mode,"depth":depth,"expected":expected,"status":status,"raw_status":raw,
            **run,"accepted":bool(ok),"k_induction":induction,"failed_assertions":failed,
            "reached_covers":reached,"control_check":check}

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--variant",choices=("P","F"),required=True)
    args=p.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):raise ValueError("new isolated build output required")
    paths=baseline_inputs()+[ROOT/"experiments/spi_phase"/n for n in ("build_timed_gpio.py","build_variants.py","run_formal.py","run_integration.py","run_program_sensitivity.py","run_timed_instruction_proof.py","formal/timed_properties.sv","formal/timed_gpio_properties.vh","formal/timed_refinement.sv")]+[ROOT/"docs/specs/spi-timed-gpio-comparison.md"]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    result={"status":"RUNNING","variant":args.variant,"started_utc":datetime.now(timezone.utc).isoformat(),
            "input_sha256":hashes,"sources":prepare(out,args.variant),"tasks":[],
            "assumptions":"initial reset only; refinement excludes new allocation space only at enabled valid compact RUN fetch"}
    result["generated_sha256"]={p.name:digest(p) for p in (out/"inputs").iterdir()}
    def save():(out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        for name,mode,top,expected,defines in (
            ("instruction","prove","timed_properties","PASS",""),
            ("refinement","prove","timed_refinement","PASS",""),
            ("covers","cover","timed_properties","PASS",""),
            ("wrong_count","bmc","timed_properties","FAIL","-D WRONG_COUNT"),
            ("wrong_update","bmc","timed_properties","FAIL","-D WRONG_UPDATE")):
            row=run_case(out,args.variant,name,mode,top,expected,defines)
            result["tasks"].append(row);save();print(name,row["status"],"accepted",row["accepted"],flush=True)
        assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in paths},"source drift"
        result["status"]="PASS" if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED"
    except Exception as error:result.update(status="HARNESS_OR_TOOL_FAILURE",error=str(error));raise
    finally:save()
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
