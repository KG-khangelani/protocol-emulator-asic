"""Preflight the same reset-width edit in the council's VM/PIO power-query fixtures."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"input changed: {old}")
    return text.replace(old,new)


def get_reference(onewire):
    spec = importlib.util.spec_from_file_location("power_query_reference",onewire/"screen.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command, directory):
    proc = subprocess.run([str(arg) for arg in command],cwd=directory,timeout=90,capture_output=True)
    if proc.returncode:
        raise RuntimeError((proc.stdout+proc.stderr).decode(errors="replace")[-2000:])
    return proc.stdout.decode()


def build(args, reference):
    stage = args.out/"build"
    stage.mkdir(exist_ok=False)
    reference.verify(args.repo)
    reference.compile_fixture(stage)
    vm = (args.onewire/"power_query.asm").read_text(encoding="utf-8")
    vm = replace_once(vm,"    WAIT cycles=24998","    WAIT cycles=25798")
    path = stage/"edit.plan"
    image = reference.make_plan(vm,path)
    if (image["words"], image["load_steps"]) != (85,712):
        raise ValueError("VM image bounds")
    pio = (args.pio_dir/"power_query.pio").read_text(encoding="utf-8")
    pio = replace_once(pio,"set x, 30                 side 1 [3]","set x, 31                 side 1 [3]")
    (stage/"edit.pio").write_text(pio,encoding="ascii")
    run([args.pio_tools/"pioasm","-o","hex","edit.pio","edit.hex"],stage)
    pio_words = [int(v,16) for v in (stage/"edit.hex").read_text(encoding="ascii").splitlines()]
    if len(pio_words) != 32:
        raise ValueError("PIO image bounds")
    result = {"vm":image, "pio_words":len(pio_words),
              "pio_little_endian_sha256":sha(b"".join(w.to_bytes(2,"little") for w in pio_words)),
              "simulator":run(["iverilog","-V"],stage).splitlines()[0], "cases":{}}
    for name, source, delay, width, stuck, parasite, expected, _ in reference.cases():
        if source != "normal":
            continue
        stdout = run(["vvp",stage/"bench.vvp",f"+plan={path}","+steps=712",f"+delay={delay}",
                      f"+width={width}",f"+stuck={stuck}",f"+parasite={parasite}"],stage)
        (stage/f"vm-{name}.log").write_text(stdout)
        result["cases"][name] = reference.inspect(stdout)
    (stage/"vm.json").write_text(json.dumps(result,indent=2)+"\n")


def score_edit(reference, edited, baseline, steps, expected):
    if edited["releases"][0] - edited["falls"][0] != 25800:
        raise ValueError("reset differs from requested 516 us")
    if baseline["releases"][0] - baseline["falls"][0] != 25000:
        raise ValueError("baseline reset")
    try:
        reference.judge(edited,steps,expected)
    except ValueError as exc:
        if str(exc) != "reset duration":
            raise
    else:
        raise ValueError("the original 500 us fixture accepted the edit")
    # Compare all measured edge positions, including terminal timing, to the
    # declared single 16 us displacement after the unchanged first falling edge.
    shifted = dict(baseline,falls=[baseline["falls"][0],*(e+800 for e in baseline["falls"][1:])],
                   releases=[e+800 for e in baseline["releases"]], halt_edge=baseline["halt_edge"]+800)
    if shifted != edited:
        raise ValueError(f"other public change: {edited} versus {shifted}")
    reference.judge(baseline,steps,expected)
    return {"width":25800,"pulses":len(edited["falls"]),"terminal_displacement_intervals":800,
            "terminal":edited["result"],"decoded":edited["decoded_wire_bytes"]}


def score(args, reference):
    stage = args.out/"build"
    if (args.out/"edit-result.json").exists():
        raise FileExistsError("choose a fresh score directory")
    result = {"started_utc":stamp(),"status":"INCOMPLETE","cases":{}}
    vm_baseline = json.loads((args.onewire/"result.json").read_bytes())
    pio_baseline_blob = args.pio_baseline.read_bytes()
    if args.pio_baseline.suffix == ".gz":
        pio_baseline_blob = gzip.decompress(pio_baseline_blob)
    pio_baseline = json.loads(pio_baseline_blob)
    vm = json.loads((stage/"vm.json").read_bytes())
    files = [args.onewire/"power_query.asm",args.onewire/"power_query_tb.sv",args.onewire/"screen.py",
             args.onewire/"result.json",args.pio_dir/"power_query.pio",args.pio_dir/"pio_trace.cjs",
             args.pio_tools/"tools.json",args.pio_baseline,Path(__file__)]
    result["source_sha256"] = [{"name":p.name,"sha256":sha(p.read_bytes())} for p in files]
    result["uncompressed_pio_baseline_sha256"] = sha(pio_baseline_blob)
    result["vm_edited_image"],result["pio_edited_image"] = vm["vm"],vm["pio_little_endian_sha256"]
    result["simulator"],result["node"] = vm["simulator"],run(["node","--version"],args.repo).strip()
    try:
        for name, source, delay, width, stuck, parasite, expected, _ in reference.cases():
            if source != "normal":
                continue
            stdout = run(["node",args.pio_dir/"pio_trace.cjs",args.pio_tools,stage/"edit.hex",
                          delay,width,stuck,parasite,"b4cc",0],args.repo)
            (stage/f"pio-{name}.log").write_text(stdout)
            vm_out = score_edit(reference,vm["cases"][name],vm_baseline["cases"][name]["observed"],712,expected)
            pio_out = score_edit(reference,reference.inspect(stdout),pio_baseline["cases"][name]["observed"],115,expected)
            if vm_out != pio_out:
                raise ValueError("wire/terminal summaries differ")
            result["cases"][name] = vm_out
        if len(result["cases"]) != 10:
            raise ValueError("missing corners")
        result["status"] = "PASS_COMMON_DIGITAL_EDIT"
    except Exception as error:
        result["failure"] = str(error)
        raise
    finally:
        result["ended_utc"] = stamp()
        (args.out/"edit-result.json").write_text(json.dumps(result,indent=2)+"\n")
    print(result["status"],len(result["cases"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=["build","score"])
    for flag in ["repo","onewire","pio-dir","pio-tools","out"]:
        parser.add_argument("--"+flag,type=Path,required=True)
    parser.add_argument("--pio-baseline",type=Path)
    args = parser.parse_args()
    for key in ["repo","onewire","pio_dir","pio_tools","out","pio_baseline"]:
        if getattr(args,key):
            setattr(args,key,getattr(args,key).resolve())
    if args.stage == "score" and not args.pio_baseline:
        parser.error("score needs --pio-baseline")
    os.chdir(args.repo)
    reference = get_reference(args.onewire)
    if args.stage == "build":
        build(args,reference)
    else:
        score(args,reference)


if __name__ == "__main__":
    main()
