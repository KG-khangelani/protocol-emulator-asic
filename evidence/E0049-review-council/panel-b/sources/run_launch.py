"""Screen an always-selected host handoff against the frozen public loader.

Run in the project workbench from the repository root with --out set to a
new writable directory. Only materialized vectors, simulator files and
compact results go there. The committed G3/G5 test suites are separate.
"""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def sha(data):
    return hashlib.sha256(data).hexdigest()


def command(args, cwd, timeout=60):
    proc = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=timeout, check=False)
    if proc.returncode:
        raise RuntimeError(f"{args[0]} returned {proc.returncode}\n{proc.stdout}")
    return proc.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root, out = args.root.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    from tools.assembler import assemble, load_plan
    from tools.production_sram import verify
    production = verify(root)
    result = {"started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "status": "INCOMPLETE", "runtime": {}, "images": [], "controls": []}
    dest = out / "result.json"
    def save():
        dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    save()
    try:
        tb = Path(__file__).with_name("launch_tb.sv").resolve()
        result["script_sha256"] = sha(Path(__file__).read_bytes())
        result["bench_sha256"] = sha(tb.read_bytes())
        result["qualified_profile_sha256"] = production["profile_sha256"]
        result["model_sha256"] = production["model_sha256"]
        result["runtime"] = {tool: command([tool, "-V"], out).splitlines()[0]
                             for tool in ("iverilog", "vvp")}
        models = []
        for name, expected in production["model_sha256"].items():
            raw = gzip.decompress((root / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" /
                                   (name + ".gz")).read_bytes())
            if sha(raw) != expected:
                raise ValueError(f"model hash mismatch for {name}")
            model = out / name
            model.write_bytes(raw)
            models.append(str(model))
        rtl = [root / "src" / (name + ".v") for name in
               ("project", "m1_engine", "m1_data_store", "m1_input_sync", "m1_program_store")]
        executable = out / "launch.vvp"
        command(["iverilog", "-g2012", "-s", "launch_tb", "-o", str(executable),
                 str(tb), *map(str, rtl), *models], out)
        inputs = sorted((root / "programs/od128-sram-v1").glob("*.asm"))
        inputs += [root / "experiments/waveform_replay" / (name + ".asm")
                   for name in ("control", "timing_fault")]
        if len(inputs) != 15:
            raise ValueError("published file census changed")
        sources = [(path.relative_to(root).as_posix(), path.read_text(encoding="utf-8"))
                   for path in inputs]
        synthetic = (".target od128-sram-v1\n.idle 2\n.data TX1 0\n"
                     "WAIT_PIN pin=1 level=1 timeout=0\nSET mask=1 value=1 oe=1\nHALT\n")
        sources.append(("synthetic_first_wait", synthetic))
        for number, (name, source) in enumerate(sources):
            image = assemble(source)
            steps = load_plan(image)["steps"]
            plan = out / f"plan-{number:02d}.txt"
            lines = []
            for step in steps:
                expected = step["expected"]
                fields = (step["action"] == "flush_idle", step["rst_n"], step["ena"], step["ui_in"],
                          step["uio_in"], step["host_drives_uio"], expected["uio_oe"],
                          expected.get("uio_out", -1), expected.get("uo_out", -1))
                lines.append(" ".join(str(int(field)) for field in fields))
            plan.write_bytes(("\n".join(lines) + "\n").encode())
            witness = name == "synthetic_first_wait"
            for mode in ((0, 1, 2, 3) if witness else (0,)):
                log = command(["vvp", str(executable), f"+PLAN={plan}", f"+MODE={mode}",
                               f"+WITNESS={int(witness)}"], out)
                observed = [line for line in log.splitlines() if line.startswith(("MATCH ", "CONTROL "))]
                if len(observed) != 1 or not observed[0].startswith("CONTROL " if mode else "MATCH "):
                    raise RuntimeError(f"missing outcome for {name} mode {mode}\n{log}")
                if mode:
                    result["controls"].append(observed[0])
                else:
                    result["images"].append({"source": name, "binary_sha256": image["binary_sha256"],
                                             "reference_disabled_steps": sum(not s["ena"] for s in steps),
                                             "result": observed[0]})
                save()
        if production != verify(root):
            raise ValueError("production changed during the experiment")
        result["status"] = "PASS_PREFIX_AND_THREE_NEGATIVE_CONTROLS"
    except Exception as exc:
        result["status"] = "FAILED"
        result["error"] = str(exc)
        raise
    finally:
        result["ended_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()
    print(result["status"], len(result["images"]), len(result["controls"]))


if __name__ == "__main__":
    main()
