"""Exercise version-bound G4/G5 assembler entry points with no installed packages or network."""
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


G4="5bdc0e6b6449a829a5da1f8f9a8060257e974843"
G5_ZIP="evidence/E0048-waveform-replay/publication/downloaded/g5-waveform-replay.zip"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def run(command,cwd,expected=0):
    proc=subprocess.run([str(v) for v in command],cwd=cwd,capture_output=True,timeout=90)
    if proc.returncode!=expected:
        raise ValueError(f"command exit {proc.returncode}, expected {expected}: {proc.stderr[-400:]!r}")
    return proc.stdout,proc.stderr


def perform(stage,program,files,expected,published_destination):
    stage.mkdir()
    for path,raw in files.items():
        target=stage/path
        target.parent.mkdir(exist_ok=True,parents=True)
        target.write_bytes(raw)
    invoke=[sys.executable,"-I","-S","-B","tools/assembler.py"]
    help_text=run([*invoke,"--help"],stage)[0].decode()
    output=run([*invoke,program,"--out",published_destination],stage)[0].decode().strip()
    generated={name:sha((stage/published_destination/name).read_bytes()) for name in expected}
    if generated!=expected:
        raise ValueError("program bytes, listing, metadata or plan changed")
    _,err=run([*invoke,program,"--out","build/unsupported","--profile","selected-power"],stage,expected=2)
    if "unrecognized arguments: --profile selected-power" not in err.decode() or (stage/"build/unsupported").exists():
        raise ValueError("unexpected CLI profile behavior")
    p=json.loads((stage/published_destination/"load-plan.json").read_bytes())
    term=[{"action":s["action"],"ena":s["ena"],"ui_hex":f'{s["ui_in"]:02x}'}
          for s in p["steps"][-2:]]
    if term != [{"action":"flush_idle","ena":0,"ui_hex":"00"}]*2:
        raise ValueError("released default changed")
    return {"published_command":f"python tools/assembler.py {program} --out {published_destination}",
            "cli_help":help_text,"output":output,"generated_sha256":generated,
            "load_steps":len(p["steps"]),"ena_low_steps":sum(s["ena"]==0 for s in p["steps"]),
            "last_two":term,"profile_error":err.decode().splitlines()[-1],
            "expected_error_exit":2,"unsupported_directory_created":False,
            "bundle_file_sha256":{k:sha(v) for k,v in files.items()}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    repo,out=args.repo.resolve(),args.out.resolve()
    out.mkdir(exist_ok=False,parents=True)
    result={"started_utc":datetime.now(timezone.utc).isoformat(),"status":"INCOMPLETE",
            "python":sys.version,"environment":"docker --network none; isolated child Python (-I -S -B)"}
    try:
        manifest=json.loads((repo/"evidence/E0047-g4-submission-candidate/publication/g4-submission.json").read_bytes())
        names=manifest["bundle_members_sha256"]
        program="programs/od128-sram-v1/uart_tx.asm"
        files={}
        for name in [program,"tools/assembler.py","docs/programming.md"]:
            data=run(["git","-C",repo,"-c",f"safe.directory={repo}","cat-file","blob",f"{G4}:{name}"],repo)[0]
            if sha(data)!=names[name]: raise ValueError("G4 reconstructed member hash")
            files[name]=data
        public=next(entry for entry in manifest["original_archives"] if entry["asset"]=="g4-public-programs.zip")
        archived=repo/public["storage"][0]["path"]
        if sha(archived.read_bytes())!=public["sha256"]: raise ValueError("public-programs archive identity")
        artifact_names=["program.bin","program.lst","program.json","load-plan.json"]
        with ZipFile(archived) as z:
            expected={name:sha(z.read("examples/uart_tx/"+name)) for name in artifact_names}
        if any(expected[k]!=names["compiled/uart_tx/"+k] for k in expected):
            raise ValueError("compiled member hashes do not match publication")
        result["g4"]=perform(out/"g4",program,files,expected,"build/my-uart")
        result["g4"]["shipped_tools_members"]=[n for n in names if n.startswith("tools/")]
        result["g4"]["archive_binding"]=public["sha256"]
        g5=repo/G5_ZIP
        if sha(g5.read_bytes())!="58901e20a08a9213024f81af1a76652c2239c9971684b88e21c27085269353ea":
            raise ValueError("G5 starter identity")
        program="experiments/waveform_replay/control.asm"
        with ZipFile(g5) as z:
            files={name:z.read(name) for name in [program,"tools/assembler.py","docs/programming.md","README.md"]}
            expected={name:sha(z.read("compiled/control/"+name)) for name in artifact_names}
            tools=[n for n in z.namelist() if n.startswith("tools/")]
        result["g5"]=perform(out/"g5",program,files,expected,"build/my-control")
        result["g5"]["shipped_tools_members"]=tools
        result["g5"]["archive_binding"]=sha(g5.read_bytes())
        result["status"]="PASS_OFFLINE_ENTRY_CHECK"
    except Exception as error:
        result["failure"]=str(error)
        raise
    finally:
        result["ended_utc"]=datetime.now(timezone.utc).isoformat()
        (out/"result.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
    print(result["status"])


if __name__=="__main__":
    main()
