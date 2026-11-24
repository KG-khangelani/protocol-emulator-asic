"""Replay the bounded SPI target and require its retained positive and failed observations."""
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_bytes())


def invoke(argv):
    completed = subprocess.run([str(item) for item in argv],capture_output=True,text=True,timeout=900)
    if completed.returncode:
        raise RuntimeError((completed.stderr+completed.stdout)[-2000:])
    return completed.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo","pdk-libs","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    parser.add_argument("--host-utilities",type=Path,default=HERE.parent,
                        help="panel C directory containing selector_orders.py and resident_replay.py")
    parser.add_argument("--image",required=True,help="existing Linux Icarus workbench image ID or digest")
    args=parser.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    for var in ("TMP","TEMP","TMPDIR"):
        os.environ[var]=str(out)
    image=invoke(["docker","image","inspect","--format","{{.Id}}",args.image])
    if not image.startswith("sha256:"): raise ValueError("missing local image ID")
    base=["docker","run","--rm","--pull=never","--network","none","--read-only"]
    for path,alias,readonly in [(args.repo.resolve(),"/repo",True),(args.host_utilities.resolve(),"/host",True),
                               (HERE,"/spi",True),(args.pdk_libs.resolve(),"/models",True),(out,"/run",False)]:
        base+=["--mount",f"type=bind,source={path},target={alias}"+(",readonly" if readonly else "")]
    base+=["--env","PYTHONPATH=/host","--env","PYTHONDONTWRITEBYTECODE=1","--env","TMPDIR=/run",
           "--workdir","/run",image,"python3","-B"]
    result={"started_utc":datetime.now(timezone.utc).isoformat(),"image":image,"status":"INCOMPLETE"}
    try:
        invoke([*base,"/spi/spi_target_screen.py","--repo","/repo","--out","/run/target","--pdk-libs","/models"])
        invoke([*base,"/spi/spi_abort_trade.py","--repo","/repo","--out","/run/trade"])
        target=load(out/"target/result.json")
        original=load(HERE/"records/target.json")
        for field in ("implementation","stronger_abort_pass","images","qualified_file_sha256","g4_netlist_sha256"):
            if target[field]!=original[field]: raise ValueError("changed target "+field)
        trade=load(out/"trade/result.json")
        reference=load(HERE/"records/trade.json")
        if trade["single_timeout"]!=reference["single_timeout"] or trade["cooperative"]!=reference["cooperative"]:
            raise ValueError("changed timeout/capacity result")
        result["status"]="REPRODUCED_COMPLETE_FRAMES_AND_ABORT_FAILURE"
        result["observations"]={name:obj["canonical_sha256"] for name,obj in target["implementation"].items()}
        result["timeout_sweep_sha256"]=trade["single_timeout"]["canonical_sha256"]
        result["miso_abort_ns"]=target["implementation"]["rtl"]["named"]["abort"]["miso_release_ns"]
    except Exception as exc:
        result["failure"]=str(exc)
        raise
    finally:
        result["ended_utc"]=datetime.now(timezone.utc).isoformat()
        (out/"replay.json").write_bytes((json.dumps(result,indent=2)+"\n").encode())
    print(result["status"])


if __name__=="__main__":
    main()
