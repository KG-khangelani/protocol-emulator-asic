# SPDX-License-Identifier: Apache-2.0
"""Retain small source/log/witness records, excluding compiled simulator/solver bulk."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
from build_variants import ROOT

def retain(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    if source.suffix in (".log",".vcd",".jsonl") or source.name=="trace.json":
        destination=destination.with_name(destination.name+".gz")
        destination.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
    else:shutil.copyfile(source,destination)

def gate(source,target):
    if not source.exists():return
    patterns=("result.json","*.log","proof.sby","proof/status","proof/engine_0/trace*.vcd",
              "inputs/*","variants/source-manifest.json","variants/*/source.patch","variants/*/src/*",
              "*/proof.sby","*/proof.log","*/proof/status","*/proof/engine_0/trace*.vcd",
              "*/inputs/*","*/transformation.json","*/*/results.xml","*/*/records/cases.jsonl",
              "*/*/records/*.json","preflight-inputs/inputs/*","preflight-inputs/preflight.json",
              "preflight-inputs/preflight/*/driver.sv","preflight-inputs/preflight/*/clock.sv",
              "preflight-inputs/preflight/*/*.log","preflight-inputs/preflight/*/trace.json")
    selected={p for pattern in patterns for p in source.glob(pattern) if p.is_file()}
    for p in sorted(selected):retain(p,target/p.relative_to(source))

def main():
    p=argparse.ArgumentParser();p.add_argument("--run",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):raise ValueError("new build output required")
    out.mkdir(parents=True)
    run=args.run.resolve();record_path=run/"result.json"
    if record_path.exists():
        retain(record_path,out/"result.json")
        record=json.loads(record_path.read_text(encoding="utf-8"))
        for label,row in record.get("gates",{}).items():
            source=Path(row.get("path",str(run/label)))
            gate(source,out/label)
    else:
        for label in ("comparison","instruction_p","instruction_f","program_p","program_f","refinement_p","refinement_f"):
            gate(run/label,out/label)
    for log in run.glob("*.log"):retain(log,out/log.name)
    files=sorted(p for p in out.rglob("*") if p.is_file())
    (out/"SHA256SUMS").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.relative_to(out).as_posix()+"\n" for p in files))
    print(f"Retained {len(files)} files")
if __name__=="__main__":main()
