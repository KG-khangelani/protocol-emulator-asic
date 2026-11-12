# SPDX-License-Identifier: Apache-2.0
"""Same compact equivalence obligations with a flattened, simplified solver input.

The hierarchical attempt is retained separately. This frontend change merges
shared logic before SMT conversion; assumptions, assertions, depth12 and 180s
remain unchanged. No timed-out task is reported as a pass.
"""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
from build_variants import ROOT,FILES
from run_formal import digest
from run_program_sensitivity import execute
from run_timed_instruction_proof import prepare

def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);p.add_argument("--variant",choices=("P","F"),required=True)
    args=p.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):raise ValueError("new isolated build output required")
    sources=prepare(out,args.variant);inputs=out/"inputs"
    paths=[ROOT/"src"/n for n in FILES]+[ROOT/"experiments/spi_phase"/n for n in (
        "build_timed_gpio.py","build_variants.py","run_formal.py","run_integration.py",
        "run_program_sensitivity.py","run_timed_instruction_proof.py","run_timed_refinement.py",
        "formal/timed_properties.sv","formal/timed_gpio_properties.vh","formal/timed_refinement.sv")]
    paths+=[ROOT/"docs/specs/spi-timed-gpio-comparison.md"]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in paths}
    files=["phase_engine.v","compact_engine.v","timed_refinement.sv","refinement_bindings.vh"]
    flags="-D VARIANT_F " if args.variant=="F" else ""
    cfg="[options]\nmode prove\ndepth 12\n\n[engines]\nsmtbmc z3\n\n[script]\n"
    cfg+="read -formal -sv "+flags+" ".join(n for n in files if not n.endswith(".vh"))+"\n"
    cfg+="prep -top timed_refinement -flatten\nopt_clean\n\n[files]\n"
    cfg+="\n".join(str(inputs/n) for n in files)+"\n"
    (out/"proof.sby").write_text(cfg)
    result={"status":"RUNNING","variant":args.variant,"started_utc":datetime.now(timezone.utc).isoformat(),
            "input_sha256":hashes,"sources":sources,"generated_sha256":{p.name:digest(p) for p in inputs.iterdir()},
            "change":"flatten and clean solver representation only; no changed assumptions/assertions/budget"}
    def save():(out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
    save()
    try:
        run=execute(["sby","-f","-d",str(out/"proof"),str(out/"proof.sby")],out/"proof.log",180)
        raw=(out/"proof/status").read_text().strip() if (out/"proof/status").exists() else "MISSING"
        match=re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}",raw)
        status=match[1] if match else "MISSING_OR_MALFORMED"
        log=(out/"proof.log").read_text()
        induction="successful proof by k-induction" in log
        result["proof"]={**run,"status":status,"raw_status":raw,"k_induction":induction,
                         "failed_assertions":re.findall(r"Assert failed in (.+)",log)}
        assert hashes=={p.relative_to(ROOT).as_posix():digest(p) for p in paths},"source drift"
        result["status"]="PASS" if run["returncode"]==0 and not run["timed_out"] and status=="PASS" and induction else "NOT_QUALIFIED"
    finally:save()
    print(args.variant,result["status"],flush=True)
    return 0 if result["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
