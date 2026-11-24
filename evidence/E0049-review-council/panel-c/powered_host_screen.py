"""Reproduce the council's powered-host digital screen using Icarus and Git blobs."""
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


G4 = "5bdc0e6b6449a829a5da1f8f9a8060257e974843"
G5 = "022834146efcb5f388a4d6ec23b3b705a0df7ef8"
BUNDLE_SHA = "58901e20a08a9213024f81af1a76652c2239c9971684b88e21c27085269353ea"
E0048 = "evidence/E0048-waveform-replay/publication/downloaded/g5-waveform-replay.zip"
MODEL_DIR = "evidence/E0042-sram-prefetch-screen/feasibility/verilog"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(command, cwd=None):
    process = subprocess.run(command, cwd=cwd, capture_output=True, timeout=90)
    if process.returncode:
        raise RuntimeError(f"{command}: {process.returncode}\n"
                           + (process.stdout + process.stderr).decode(errors="replace")[-3000:])
    return process.stdout


def blob(repo, revision, path):
    return run(["git", "-C", str(repo), "-c", f"safe.directory={repo}",
                "cat-file", "blob", f"{revision}:{path}"])


def utc():
    return datetime.now(timezone.utc).isoformat()


def stimulus(plan, name, idle, variant, runtime_edges):
    rows = []
    corrupted = False
    for step in plan:
        selector = step["ui_in"]
        enable = step["ena"] if variant == "reference" else 1
        if variant in ("powered", "corrupt") and step["action"] == "flush_idle":
            selector = 0xe7
        data = step["uio_in"]
        if variant == "corrupt" and step["action"] == "write_byte" and not corrupted:
            data ^= 1
            corrupted = True
        bias = idle if step["action"] == "flush_idle" else 0
        rows.append((step["rst_n"], enable, selector, step["host_drives_uio"], data, bias))
    for edge in range(1, runtime_edges + 1):
        bias = (idle | 0x80) if name in ("control", "timing_fault") and edge >= 8 else idle
        rows.append((1, 1, 0, False, 0, bias))
    return "".join(" ".join(f"{value:x}" for value in row) + "\n" for row in rows).encode()


def check_load(plan, records):
    failures = []
    for index, (step, (status, oe, pads)) in enumerate(zip(plan, records, strict=True)):
        observed = {"uo_out": status, "uio_oe": oe, "uio_out": pads}
        for signal, expected in step["expected"].items():
            if observed[signal] != expected:
                failures.append({"index_from_zero": index, "action": step["action"],
                                 "signal": signal, "expected": expected, "observed": observed[signal]})
    return failures


def check_runtime(name, trace, expectation):
    errors = []
    for edge, (status, oe, pads) in enumerate(trace, 1):
        if name == "uart_tx":
            bit = 1
            if 3 <= edge < 8683:
                slot = (edge - 3) // 434
                within = slot % 10
                payload = [0x55, 0xaa][slot // 10]
                bit = 0 if within == 0 else 1 if within == 9 else (payload >> (within - 1)) & 1
            if oe != 1 or (pads & 1) != bit or (edge >= 8683 and status != 0xa7):
                errors.append(edge)
        elif name in ("control", "timing_fault"):
            value, mask = expectation["runtime_initial"]
            for relative, event_value, event_mask in expectation["events"][name]:
                if edge >= 11 + relative:
                    value, mask = event_value, event_mask
            terminal = 11 + expectation["halt_relative_edge"]
            if (oe != mask or (pads & 7) != value
                    or (edge >= terminal and status != expectation["terminal_status"])):
                errors.append(edge)
    return errors


def parse_trace(raw):
    records = []
    for line in raw.splitlines():
        if line.startswith(b"EDGE "):
            _, index, status, oe, pads = line.split()
            if int(index) != len(records):
                raise ValueError("duplicate or missing recorded edge")
            records.append(tuple(int(word, 16) for word in (status, oe, pads)))
    return records


def compile_chip(repo, out, result):
    lock = json.loads(blob(repo, G4, "tools/production-profile.json"))
    source = out / "inputs"
    source.mkdir()
    paths = []
    result["simulated_input_sha256"] = {}
    for name, expected in lock["files_sha256"].items():
        if name.startswith("src/") and name.endswith(".v"):
            raw = blob(repo, G4, name)
            if sha(raw) != expected:
                raise ValueError(f"RTL lock mismatch for {name}")
            path = source / Path(name).name
            path.write_bytes(raw)
            paths.append(str(path))
            result["simulated_input_sha256"][name] = sha(raw)
    if len(paths) != 5:
        raise ValueError("expected five production RTL files")
    for name, expected in lock["model_sha256"].items():
        raw = gzip.decompress(blob(repo, G4, f"{MODEL_DIR}/{name}.gz"))
        if sha(raw) != expected:
            raise ValueError(f"vendor model lock mismatch for {name}")
        path = source / name
        path.write_bytes(raw)
        paths.append(str(path))
        result["simulated_input_sha256"][name] = sha(raw)
    bench = Path(__file__).resolve().with_name("powered_host_tb.v")
    result["bench_sha256"] = sha(bench.read_bytes())
    command = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-s", "powered_host_tb",
               "-o", str(out / "bench.vvp"), str(bench), *paths]
    result["compile_command"] = command
    run(command, cwd=out)


def evaluate(repo, out, result):
    compile_chip(repo, out, result)
    catalog = json.loads(blob(repo, G4, "programs/od128-sram-v1/examples.json"))["examples"]
    expected = json.loads(blob(repo, G5, "experiments/waveform_replay/expected.json"))
    bundle_path = repo / E0048
    if sha(bundle_path.read_bytes()) != BUNDLE_SHA:
        raise ValueError("retained G5 release bundle hash mismatch")
    result["bundle_sha256"] = BUNDLE_SHA
    names = [entry["name"] for entry in catalog] + ["control", "timing_fault"]
    (out / "traces").mkdir()
    for label, commit in [("g4", G4), ("g5", G5)]:
        (out / f"assembler-{label}.py").write_bytes(blob(repo, commit, "tools/assembler.py"))
    negative_naive = 0
    with ZipFile(bundle_path) as bundle:
        if bundle.read("tools/assembler.py") != (out / "assembler-g5.py").read_bytes():
            raise ValueError("G5 release assembler mismatch")
        for name in names:
            g5 = name in ("control", "timing_fault")
            assembler = out / ("assembler-g5.py" if g5 else "assembler-g4.py")
            entry = next((item for item in catalog if item["name"] == name), None)
            path = f"experiments/waveform_replay/{name}.asm" if g5 else f"programs/od128-sram-v1/{entry['file']}"
            source = out / (name + ".asm")
            source.write_bytes(blob(repo, G5 if g5 else G4, path))
            dest = out / "compiled" / name
            run([sys.executable, "-I", "-B", str(assembler), str(source), "--out", str(dest)], cwd=out)
            image = json.loads((dest / "program.json").read_bytes())
            if g5:
                for asset in ("program.bin", "program.json", "program.lst", "load-plan.json"):
                    if (dest / asset).read_bytes() != bundle.read(f"compiled/{name}/{asset}"):
                        raise ValueError(f"G5 artifact mismatch: {name}/{asset}")
            elif (image["words"] != entry["expected_words"]
                  or sha((dest / "program.bin").read_bytes()) != entry["binary_sha256"]):
                raise ValueError(f"G4 independent catalog mismatch: {name}")
            plan = json.loads((dest / "load-plan.json").read_bytes())["steps"]
            runtime_edges = 8691 if name == "uart_tx" else 80
            info = {"words": len(image["words"]), "load_steps": len(plan),
                    "requests_ena_low": sum(step["ena"] == 0 for step in plan),
                    "binary_sha256": sha((dest / "program.bin").read_bytes()),
                    "runtime_edges": runtime_edges, "variants": {}}
            result["examples"][name] = info
            variants = ["reference", "naive", "powered"]
            if name == "i2c_write_read":
                variants.append("corrupt")
            reference = None
            for variant in variants:
                stim = stimulus(plan, name, image["idle_inputs"], variant, runtime_edges)
                stim_path = out / "stimulus.txt"
                stim_path.write_bytes(stim)
                raw = run(["vvp", str(out / "bench.vvp"), "+STIMULUS=" + str(stim_path)], cwd=out)
                records = parse_trace(raw)
                if len(records) != len(plan) + runtime_edges:
                    raise ValueError("incomplete runtime timeline")
                failures = check_load(plan, records[:len(plan)])
                trace = records[len(plan):]
                errors = check_runtime(name, trace, expected)
                trace_raw = b"".join(bytes(row) for row in trace)
                name_ending = f"{name}-{variant}.trace.gz"
                (out / "traces" / name_ending).write_bytes(gzip.compress(raw, mtime=0))
                mismatch = None
                if variant == "reference":
                    reference = trace
                else:
                    mismatch = next((edge for edge, pair in enumerate(zip(reference, trace, strict=True), 1)
                                     if pair[0] != pair[1]), None)
                info["variants"][variant] = {
                    "load_failed_checks": len(failures),
                    "first_load_failure": failures[0] if failures else None,
                    "first_runtime_difference_from_reference": mismatch,
                    "first_oracle_failure": errors[0] if errors else None,
                    "oracle": name if (g5 or name == "uart_tx") else None,
                    "stimulus_sha256": sha(stim), "runtime_sha256": sha(trace_raw),
                }
                if variant in ("reference", "powered") and (failures or mismatch or errors):
                    result["rejections"].append([name, variant, "positive path mismatch"])
                if variant == "naive" and any(f["action"] == "flush_idle" for f in failures):
                    negative_naive += 1
                if variant == "corrupt":
                    first_read = next(i for i, step in enumerate(plan) if step["action"] == "read_byte_after_edge")
                    if not failures or failures[0]["index_from_zero"] != first_read:
                        result["rejections"].append([name, variant, "corrupt first byte not caught at readback"])
    result["naive_examples_failing_flush"] = negative_naive
    if not negative_naive:
        result["rejections"].append(["all", "naive", "no counterexample"])
    result["status"] = "REJECTED" if result["rejections"] else "PASS_BOUNDED_DIGITAL_SCREEN"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    args = parser.parse_args()
    repo, out = args.repo.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = {"status": "INCOMPLETE", "started_utc": utc(), "source_g4": G4, "source_g5": G5,
              "image_identity_supplied_by_invoker": args.image_id, "python": sys.version,
              "runner_sha256": sha(Path(__file__).read_bytes()), "examples": {}, "rejections": []}
    try:
        result["iverilog"] = run(["iverilog", "-V"]).decode().splitlines()[0]
        result["vvp"] = subprocess.run(["vvp", "-V"], capture_output=True, check=True).stderr.decode().splitlines()[0]
        evaluate(repo, out, result)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        result["ended_utc"] = utc()
        result["runtime_seconds"] = round(time.monotonic() - start, 3)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"], len(result["examples"]), result["runtime_seconds"])
    return 1 if result["rejections"] else 0


if __name__ == "__main__":
    sys.exit(main())
