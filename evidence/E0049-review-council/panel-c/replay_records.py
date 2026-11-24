"""Replay panel C's retained positive and negative observations in fresh scratch."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent


def read_record(path):
    return json.loads(path.read_bytes())


def run(command, root, *, expected_failure=False):
    proc = subprocess.run([str(v) for v in command],cwd=root, text=True,capture_output=True, timeout=1200)
    if bool(proc.returncode) != expected_failure:
        raise RuntimeError(f"unexpected exit {proc.returncode}: {(proc.stdout+proc.stderr)[-1800:]}")
    return proc.stdout


def bind(path, target, *, writable=False):
    return ["--mount",f"type=bind,source={path},target={target}" + ("" if writable else ",readonly")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ["repo","out","pdk-libs"]:
        parser.add_argument("--"+flag, required=True,type=Path)
    parser.add_argument("--image",required=True,help="already available Linux workbench image selector")
    parser.add_argument("--pio-tools",type=Path,help="optional directory from panel A's pinned PIO tools fetcher")
    args = parser.parse_args()
    repo, out, models = args.repo.resolve(), args.out.resolve(), args.pdk_libs.resolve()
    out.mkdir(exist_ok=False,parents=True)
    for var in ["TMPDIR","TEMP","TMP"]:
        os.environ[var] = str(out)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    image = run(["docker","image","inspect","--format","{{.Id}}",args.image],repo).strip()
    if not image.startswith("sha256:"):
        raise ValueError("could not identify the local image")
    base = ["docker","run","--rm","--pull=never","--network","none","--read-only",
            *bind(repo,"/repo"),*bind(HERE,"/scripts"),*bind(out,"/run",writable=True),*bind(models,"/models"),
            "--workdir","/run","--env","TMPDIR=/run","--env","PYTHONDONTWRITEBYTECODE=1"]

    def docker(script,arguments,*,expected_failure=False,extra=()):
        return run([*base,*extra,image,"python3","-I","-B",script,*arguments],repo,
                   expected_failure=expected_failure)

    def test(script, dest,*,extras=(),expected_failure=False):
        docker("/scripts/"+script,["--repo","/repo","--out","/run/"+dest,"--image-id",image,*extras],
               expected_failure=expected_failure)
        return read_record(out/dest/"result.json")

    summary = {"started_utc":datetime.now(timezone.utc).isoformat(),"local_image_id":image,
               "image_selector":args.image,"status":"INCOMPLETE","checks":{}}
    checks = summary["checks"]
    try:
        old = out/"initial-launch-kit"
        old.mkdir()
        shutil.copyfile(HERE/"powered_host_screen.py",old/"powered_host_screen.py")
        shutil.copyfile(HERE/"records/launch-initial-tb.v",old/"powered_host_tb.v")
        docker("/run/initial-launch-kit/powered_host_screen.py",
               ["--repo","/repo","--out","/run/launch-initial","--image-id",image],expected_failure=True)
        initial = read_record(out/"launch-initial/result.json")
        if initial["failure"] != "invalid literal for int() with base 16: b'Xx'":
            raise ValueError(f"first launch failure changed: {initial.get('failure')}")
        checks["initial_launch_failure"] = initial["failure"]

        launch = test("powered_host_screen.py","launch")
        if launch["status"] != "PASS_BOUNDED_DIGITAL_SCREEN":
            raise ValueError("powered launch")
        projection = json.loads(run([sys.executable,"-I","-B",HERE/"board_observation.py",out/"launch"],repo))
        if projection != read_record(HERE/"records/launch-pad-only.json"):
            raise ValueError("powered launch pad projection")
        checks["launch_pad_projection"] = projection

        order = test("selector_orders.py","orders",extras=["--pdk-libs","/models"])
        retained_order = read_record(HERE/"records/selector-orders.json")
        if order["status"] != "PASS_SETTLED_ORDER_SCREEN" or order["sampled"] != retained_order["sampled"]:
            raise ValueError("selector observations")
        checks["selector_order_samples_per_implementation"] = order["sampled"]["rtl"]["rows"]

        test("resident_replay.py","resident-strict",extras=["--pdk-libs","/models"],expected_failure=True)
        stale = read_record(out/"resident-strict/rtl/observations.json")
        captured = read_record(HERE/"records/resident-strict-observations.json")
        if stale.get("failure") != captured["failure"] or stale["warm_B"] != captured["warm_B"]:
            raise ValueError("resident raw-trace rejection changed")
        checks["strict_resident_equality_rejected"] = True
        valid = test("resident_replay.py","resident-valid",extras=["--pdk-libs","/models","--condition","valid-gated"])
        observed = read_record(out/"resident-valid/rtl/observations.json")
        if valid["status"] != "PASS_VALID_GATED_DIAGNOSTIC" or observed != read_record(HERE/"records/resident-valid-observations.json"):
            raise ValueError("resident valid-gated check")
        if set(valid["dut_results"].values()) != set(read_record(HERE/"records/resident-valid.json")["dut_results"].values()):
            raise ValueError("resident RTL/gate results")
        checks["resident_observations_sha256"] = hashlib.sha256((out/"resident-valid/rtl/observations.json").read_bytes()).hexdigest()

        run([sys.executable,"-I","-B",HERE/"starter_audit.py","--repo",repo,"--out",out/"starter"],repo)
        starter = read_record(out/"starter/results.json")
        if starter["artifacts"] != read_record(HERE/"records/starter.json")["artifacts"]:
            raise ValueError("standalone starter artifacts")
        checks["standalone_artifacts"] = len(starter["artifacts"])
        costs = json.loads(run([sys.executable,"-I","-B",HERE/"delivery_metrics.py","--repo",repo],repo))
        if costs != read_record(HERE/"records/delivery-metrics.json"):
            raise ValueError("release or physical job arithmetic")
        checks["delivery_costs"] = "matched"

        if args.pio_tools:
            pio_tools = args.pio_tools.resolve()
            onewire = "evidence/E0049-review-council/onewire"
            pio = "evidence/E0049-review-council/panel-a/pio"
            (out/"edit").mkdir()
            docker("/scripts/edit_task.py",["build","--repo","/repo","--onewire","/repo/"+onewire,
                   "--pio-dir","/repo/"+pio,"--pio-tools","/pt","--out","/run/edit"],extra=bind(pio_tools,"/pt"))
            run([sys.executable,"-I","-B",HERE/"edit_task.py","score","--repo",repo,"--onewire",repo/onewire,
                 "--pio-dir",repo/pio,"--pio-tools",pio_tools,"--out",out/"edit",
                 "--pio-baseline",repo/pio/"results.json.gz"],repo)
            edit = read_record(out/"edit/edit-result.json")
            if edit["status"] != "PASS_COMMON_DIGITAL_EDIT" or edit["cases"] != read_record(HERE/"records/common-edit.json")["cases"]:
                raise ValueError("shared source-edit case matrix")
            checks["common_vm_pio_edit_cases_per_implementation"] = len(edit["cases"])
        summary["status"] = "PASS_PANEL_C_REPLAY"
    except Exception as error:
        summary["failure"] = str(error)
        raise
    finally:
        summary["ended_utc"] = datetime.now(timezone.utc).isoformat()
        (out/"replay-result.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(summary["status"],len(checks),"checks")


if __name__ == "__main__":
    main()
