# SPDX-License-Identifier: Apache-2.0
"""Run or assemble the frozen four-design comparison with all required proof gates."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
from build_variants import ROOT
from run_formal import digest
from run_program_sensitivity import execute

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    for label in ("comparison","instruction-p","instruction-f","program-p","program-f","refinement-p","refinement-f"):
        p.add_argument("--"+label,type=Path)
    args=p.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):raise ValueError("new isolated build output required")
    out.mkdir(parents=True)
    labels=("comparison","instruction_p","instruction_f","program_p","program_f","refinement_p","refinement_f")
    supplied=[getattr(args,n) for n in labels]
    if any(supplied) and not all(supplied):raise ValueError("supply all seven completed gates or none")
    record={"status":"RUNNING","started_utc":datetime.now(timezone.utc).isoformat(),"gates":{},
            "decision":"PENDING","physical":"NOT_EVALUATED","production":"UNCHANGED"}
    def save():(out/"result.json").write_text(json.dumps(record,indent=2)+"\n")
    save()
    try:
        results={}
        for label in labels:
            provided=getattr(args,label)
            directory=provided.resolve() if provided else out/label
            if provided is None:
                if label=="comparison":
                    script="run_timed_gpio.py";extra=[];limit=10800
                else:
                    kind,variant=label.split("_")
                    script="run_timed_refinement.py" if kind=="refinement" else "run_timed_"+kind+"_proof.py"
                    extra=["--variant",variant.upper()];limit=1500
                run=execute([sys.executable,str(ROOT/"experiments/spi_phase"/script),"--output",str(directory),*extra],out/(label+".log"),limit)
                record["gates"][label]={"run":run}
            r=json.loads((directory/"result.json").read_text(encoding="utf-8"));results[label]=r
            record["gates"].setdefault(label,{}).update(path=str(directory),status=r["status"],result_sha256=digest(directory/"result.json"))
            save()
        expected={"comparison":"PASS_PUBLIC_AND_GENERIC_COMPARISON_FORMAL_PENDING",
                  "program_p":"PROVED_TIMED_MODE1_MODE3_WITH_CHECKED_CONTROLS",
                  "program_f":"PROVED_TIMED_MODE1_MODE3_WITH_CHECKED_CONTROLS"}
        assert all(results[n]["status"]==status for n,status in expected.items()),"required gate did not qualify"
        qualified={}
        for variant in ("p","f"):
            instruction=results["instruction_"+variant]
            assert instruction["status"] in ("PASS","NOT_QUALIFIED"),"instruction harness failed"
            tasks={t["name"]:t for t in instruction["tasks"]}
            assert set(tasks)=={"instruction","refinement","covers","wrong_count","wrong_update"}
            assert all(tasks[n]["accepted"] for n in ("instruction","covers","wrong_count","wrong_update"))
            assert tasks["refinement"]["accepted"] or tasks["refinement"]["timed_out"],"conflicting refinement outcome"
            refinement=results["refinement_"+variant]
            assert instruction["generated_sha256"]==refinement["generated_sha256"],"changed refinement obligations"
            assert refinement["status"]=="PASS" or refinement["proof"]["timed_out"],"unexpected refinement failure"
            qualified[variant.upper()]="PASS" if refinement["status"]=="PASS" else "INCONCLUSIVE_REFINEMENT_TIMEOUT"
        record["candidate_qualification"]=qualified
        record["refinement_frontend"]="flattened proof is required; hierarchical attempts retained with their original statuses"
        hashes={}
        for label,r in results.items():
            for name,sha in r["input_sha256"].items():
                assert digest(ROOT/name)==sha,(label,"source drift",name)
                if name in hashes:assert hashes[name]==sha,("inconsistent input",name)
                hashes[name]=sha
        self_path=Path(__file__).resolve()
        hashes[self_path.relative_to(ROOT).as_posix()]=digest(self_path)
        record["input_sha256"]=hashes
        c=results["comparison"]
        assert c["cross_simulator_records_identical"] and c["cross_variant_spi_contract_traces_identical"]
        assert c["reference"]=={"P":{"paired_byte_positives":3072},"F":{"paired_byte_positives":3072}}
        for variant in ("P","F","compact10"):
            for sim in ("icarus","verilator"):
                counts=c["public"][variant][sim]
                assert (counts["cases"],counts["positive"],counts["expected_negative"])==(1052,1048,4)
        m=c["measurements"];baseline=m["compact10"]
        candidates=[v for v in ("P","F") if qualified[v]=="PASS" and m[v]["primitive_cells"]<baseline["primitive_cells"] and m[v]["state_bits"]<baseline["state_bits"]]
        winner=min(candidates,key=lambda v:(m[v]["primitive_cells"],m[v]["state_bits"],v!="P")) if candidates else None
        record.update(status="QUALIFIED_COMPARISON" if winner else "COMPARISON_COMPLETE_NO_QUALIFIED_WINNER",measurements=m,selected_candidate=winner,
                      decision="ADVANCE_"+winner+"_EXPERIMENT_ONLY" if winner else "NO_CLEAR_WINNER",
                      scope="mode1/3 normal-program proof; instruction safety and scoped compact refinement; public held mode0/2 compatibility")
    except Exception as error:record.update(status="NOT_QUALIFIED",error=str(error));raise
    finally:save()
    print(json.dumps({k:record[k] for k in ("status","decision","selected_candidate","measurements")},indent=2))
    return 0
if __name__=="__main__":raise SystemExit(main())
