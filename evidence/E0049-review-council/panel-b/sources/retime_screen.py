"""Preserve the original low period while moving the controller's data transition."""
import argparse
from dataclasses import replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import cocotb
from guard_screen import guarded, measure, save, sha, utc, witness


def retime(source, clocks):
    program = guarded(source, clocks)
    return program.replace("WAIT cycles=260", f"WAIT cycles={260 - clocks}")


def reference_events(trace, report):
    edges = [(r["t"], r["bus"] & 1) for p, r in zip(trace, trace[1:])
             if (p["bus"] ^ r["bus"]) & 1]
    boundary = [(e["kind"], e["t"]) for e in report["events"] if e["kind"] != "BIT"]
    return {"scl_transitions": edges, "boundaries": boundary, "halt": report["halt"]}


@cocotb.test()
async def retimed_transactions(dut):
    root = Path(os.environ["COUNCIL_REPO"])
    out = Path(os.environ["I2C_GENERAL_RECORD_DIR"])
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "test"))
    from test import edge, initialise
    from test_i2c_general_public import load_and_check
    from experiments.i2c.public_bus import run_bus
    from experiments.i2c.target import Target
    from tools.assembler import assemble
    from tools.i2c_oracle import Transaction, assess
    from tools.production_sram import verify

    original, identity = witness(root)
    prior = original["record"]
    case = Transaction(kind=prior["kind"], address=prior["address"], tx=prior["tx"], rx=prior["rx"])
    data = {int(reg): value for reg, value in original["data"].items()}
    baseline = reference_events(original["trace"], assess(original["trace"], case))
    source = (root / "programs/od128-sram-v1/i2c_write_read.asm").read_text(encoding="utf-8")
    assert assemble(source)["words"] == original["words"]
    images = {k: assemble(retime(source, k)) for k in (8, 24, 170, 171)}
    production = verify(root)
    result = {"started_utc": utc(), "source": "retimed public Icarus RTL, ideal bus and historical loader",
              "profile_sha256": production["profile_sha256"], "witness": identity,
              "script_sha256": sha(Path(__file__).read_bytes()), "reference_trace_sha256": prior["trace_sha256"],
              "reference_event_counts": {"scl_transitions": len(baseline["scl_transitions"]),
                                         "boundaries": baseline["boundaries"], "halt": baseline["halt"]},
              "images": {k: {"binary_sha256": i["binary_sha256"], "words": len(i["words"])}
                         for k, i in images.items()}, "accepted_by_class": {}, "rejected_expectations": [],
              "unextended": [], "nack": [], "timeout_cleanup_ideal_ticks": []}
    save(out / "result.json", result)
    work = [(f"plain-{k}", k, case, {}, "plain") for k in images]
    work += [(f"nack-{where}", 24, replace(case, nack=where), {}, "nack")
             for where in ("address", "data", "read_address")]
    for release in range(1, 39):
        for label, delay in (("before", 199987), ("final", 199991), ("late", 199992), ("forever", None)):
            timed = release if label in ("late", "forever") else None
            work.append((f"{label}-{release}", 24, replace(case, timeout_release=timed),
                         {release: delay}, label))
    for name, k, intent, stretches, group in work:
        image = images[k]
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_and_check(dut, [int(w, 16) for w in image["words"]], data)
        target = Target(intent, response=prior["response"], stretches=stretches)
        rows = await run_bus(dut, target, bound_ticks=350000, extended_pc=True)
        initial = next(i for i, r in enumerate(rows) if (r["oe"], r["out"], r["bus"]) == (28, 0, 3))
        assert all(r["out"] & r["oe"] & 3 == 0 for r in rows[:initial+1])
        offset = rows[initial]["t"]
        trace = [dict(r, t=r["t"]-offset) for r in rows[initial:]]
        raw = (json.dumps(trace, sort_keys=True, separators=(",", ":")) + "\n").encode()
        report = assess(trace, intent)
        errors = sorted({e["kind"] for e in report["errors"]})
        want = ["data_valid_delay"] if k == 171 else []
        record = {"test": name, "clocks": k, "nack": intent.nack, "stretches": stretches,
                  "expected_outcome": intent.outcome, "oracle_error_kinds": errors,
                  "expected_oracle_errors": want, "trace_sha256": sha(raw),
                  "releases": report["releases"], "halt_tick": report["halt"],
                  "observed_terminal_marker": (trace[-1]["out"] >> 2) & 7}
        matched = errors == want
        if group == "plain":
            events = reference_events(trace, report)
            record.update({"matched_original_event_times": {key: vals == baseline[key] for key, vals in events.items()},
                           "timing": measure(trace, report), "rx": trace[-1]["rx"], "rx_valid": trace[-1]["rx_valid"],
                           "fastest_ideal_hz": report["fastest_hz"], "events": events["boundaries"]})
            if not all(record["matched_original_event_times"].values()):
                matched = False
            result["unextended"].append(record)
            (out / f"{name}.json.gz").write_bytes(gzip.compress(raw, mtime=0))
        elif group == "nack":
            result["nack"].append(record)
        if intent.timeout_release is not None:
            releases = [r["t"] for p, r in zip(trace, trace[1:]) if (p["oe"] & 1) and not (r["oe"] & 1)]
            cleanup = report["halt"] - (releases[intent.timeout_release-1] + 200000)
            record["halt_ticks_after_deadline"] = cleanup
            result["timeout_cleanup_ideal_ticks"].append(cleanup)
        if matched:
            result["accepted_by_class"][group] = result["accepted_by_class"].get(group, 0) + 1
        else:
            result["rejected_expectations"].append(name)
            if len(result["rejected_expectations"]) <= 5:
                (out / f"failed-{name}.json.gz").write_bytes(gzip.compress(raw, mtime=0))
        record["expectation_matched"] = matched
        with (out / "cases.jsonl").open("a", encoding="utf-8") as journal:
            journal.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        save(out / "result.json", result)
    cleanup = result.pop("timeout_cleanup_ideal_ticks")
    result["timeout_cleanup_ideal_ticks"] = {"min": min(cleanup), "max": max(cleanup), "count": len(cleanup)}
    result["total"] = len(work)
    result["ended_utc"] = utc()
    result["cases_sha256"] = sha((out / "cases.jsonl").read_bytes())
    save(out / "result.json", result)
    assert len(work) == 159 and not result["rejected_expectations"], result["rejected_expectations"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    out, root = args.out.resolve(), args.root.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    from tools.production_sram import verify
    production = verify(root)
    for name in ("Makefile", "tb.v"):
        shutil.copy2(root / "test" / name, out / name)
    for name in ("guard_screen.py", "retime_screen.py"):
        shutil.copy2(Path(__file__).with_name(name), out / name)
    for name, expected in production["model_sha256"].items():
        raw = gzip.decompress((root / "evidence/E0042-sram-prefetch-screen/feasibility/verilog"/
                               (name + ".gz")).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == expected
        (out / name).write_bytes(raw)
    env = dict(os.environ, I2C_GENERAL_VARIANT="od128", I2C_GENERAL_RECORD_DIR=str(out),
               COUNCIL_REPO=str(root), PYTHONHASHSEED="0", COCOTB_RANDOM_SEED="20261124")
    command = ["make", "-C", str(out), f"SRC_DIR={root/'src'}", "SIM=icarus", f"SIM_BUILD={out/'sim'}",
               "COCOTB_TEST_MODULES=retime_screen", f"COCOTB_RESULTS_FILE={out/'results.xml'}",
               "GENERAL_IO=yes", "G2_CURRENT=yes", "G2_SRAM=yes", f"SRAM_MODEL_DIR={out}",
               "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
    proc = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, check=False, timeout=720)
    (out / "run.log").write_text(proc.stdout, encoding="utf-8")
    print(proc.stdout)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
