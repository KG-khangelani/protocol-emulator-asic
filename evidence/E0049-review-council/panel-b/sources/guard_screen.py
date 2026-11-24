"""Re-run one retained G4 I2C transaction on unmodified RTL with firmware guards."""
import argparse
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import cocotb


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def guarded(source, clocks):
    if clocks == 0:
        return source
    lines = []
    for line in source.splitlines():
        lines.append(line)
        if line.strip() == "SET mask=0x01 value=0x00 oe=0x01":
            lines.append(f"    WAIT cycles={clocks - 1}")
    return "\n".join(lines) + "\n"


def witness(root):
    directory = root / "evidence/E0047-g4-submission-candidate/ci-43543626249"
    evidence = json.loads((directory / "result.json").read_bytes())
    member = "output/i2c/write_read-96.json"
    artifact = evidence["archives"]["gatelevel_test_results"]
    archive = directory / f"{artifact['id']}.zip"
    with archive.open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == artifact["sha256"]
    with zipfile.ZipFile(archive) as z:
        raw = z.read(member)
    index = json.loads((directory / "zip-files.json").read_bytes())
    assert sha(raw) == index["gatelevel_test_results"][member]
    return json.loads(raw), {"g4_commit": evidence["source_commit"], "run_id": evidence["run_id"],
                             "archive_id": artifact["id"], "archive_sha256": artifact["sha256"],
                             "member": member, "member_sha256": sha(raw)}


def measure(rows, report):
    last_fall = last_rise = None
    last_data = 0
    lows, highs, setups, changes = [], [], [], []
    for a, b in zip(rows, rows[1:]):
        scl_a, scl_b = a["bus"] & 1, b["bus"] & 1
        sda_a, sda_b = a["bus"] & 2, b["bus"] & 2
        t = 5 * b["t"]
        if scl_a and not scl_b:
            if last_rise is not None:
                highs.append(t - last_rise)
            last_fall = t
        if sda_a != sda_b and not scl_a and not scl_b:
            assert last_fall is not None
            chip = bool((a["oe"] ^ b["oe"]) & 2)
            target = bool((a["target_oe"] ^ b["target_oe"]) & 2)
            assert chip or target
            owner = "both" if chip and target else "controller" if chip else "target"
            changes.append({"owner": owner, "direction": "rise" if sda_b else "fall",
                            "scl_fall_ns": last_fall, "sda_ns": t, "gap_ns": t-last_fall})
            last_data = t
        if not scl_a and scl_b:
            if last_fall is not None:
                lows.append(t - last_fall)
            setups.append(t-last_data)
            last_rise = t
    controller_falls = [c for c in changes if c["owner"] == "controller" and c["direction"] == "fall"]
    first = min(controller_falls, key=lambda c: c["gap_ns"])
    # A first-order fall from VDD to zero. tf is the time from 70% to 30%.
    ratio = math.log(0.7/0.3)
    projections = []
    for scl, sda in ((10, 10), (20, 20), (100, 20), (300, 20)):
        margin = first["gap_ns"] + (-math.log(0.7)*sda + math.log(0.3)*scl)/ratio
        projections.append({"tf_scl_ns": scl, "tf_sda_ns": sda, "ordering_margin_ns": round(margin, 4)})
    return {"min_ideal_low_ns": min(lows), "min_ideal_high_ns": min(highs),
            "min_ideal_period_ns": 5*min(report["periods"]), "min_ideal_setup_ns": min(setups),
            "earliest_controller_fall": first, "controller_sda_falls": len(controller_falls),
            "ideal_low_changes": {owner: {"count": len(values), "min_ns": min(values), "max_ns": max(values)}
                                  for owner in ("controller", "target", "both")
                                  if (values := [c["gap_ns"] for c in changes if c["owner"] == owner])},
            "offline_falling_pair_projections": projections}


@cocotb.test()
async def guarded_replay(dut):
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
    assert not prior["stretches"] and prior["response"] == 690 and prior["accepted"]
    source = (root / "programs/od128-sram-v1/i2c_write_read.asm").read_text(encoding="utf-8")
    assert assemble(source)["words"] == original["words"]
    production = verify(root)
    results = {"started_utc": utc(), "method": "ideal closed-loop RTL plus offline first-order falling-edge projection",
               "profile_sha256": production["profile_sha256"], "script_sha256": sha(Path(__file__).read_bytes()),
               "witness": identity, "reference_trace_sha256": prior["trace_sha256"],
               "case": case.__dict__, "response_ticks": prior["response"], "variants": []}
    save(out / "result.json", results)
    for clocks in (0, 8, 24, 200):
        variant = guarded(source, clocks)
        image = assemble(variant)
        words = [int(x, 16) for x in image["words"]]
        data = {int(reg): value for reg, value in original["data"].items()}
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_and_check(dut, words, data)
        target = Target(case, response=prior["response"])
        rows = await run_bus(dut, target, bound_ticks=200000, extended_pc=True)
        initial = next(i for i, r in enumerate(rows) if (r["oe"], r["out"], r["bus"]) == (28, 0, 3))
        assert all(r["out"] & r["oe"] & 3 == 0 for r in rows[:initial+1])
        offset = rows[initial]["t"]
        trace = [dict(r, t=r["t"]-offset) for r in rows[initial:]]
        trace_bytes = (json.dumps(trace, sort_keys=True, separators=(",", ":")) + "\n").encode()
        report = assess(trace, case)
        errors = sorted({e["kind"] for e in report["errors"]})
        result = {"added_clocks": clocks, "wait_operand": clocks-1 if clocks else None,
                  "source_sha256": image["source_sha256"], "binary_sha256": image["binary_sha256"],
                  "words": len(words), "spare_words": 128-len(words), "trace_sha256": sha(trace_bytes),
                  "rows": len(trace), "release_count": report["releases"], "terminal_tick": report["halt"],
                  "terminal_rx": trace[-1]["rx"], "terminal_rx_valid": trace[-1]["rx_valid"],
                  "decoded_by_target": target.decoded, "oracle_error_kinds": errors,
                  "oracle_first_errors": report["errors"][:4], "fastest_ideal_hz": report["fastest_hz"],
                  "timing": measure(trace, report)}
        results["variants"].append(result)
        # The deterministic event stream fits in a few KiB compressed.
        (out / f"trace-{clocks}.json.gz").write_bytes(gzip.compress(trace_bytes, mtime=0))
        save(out / "result.json", results)
    baseline, small, large, negative = results["variants"]
    checks = {"unaltered_trace_matches_g4": baseline["trace_sha256"] == prior["trace_sha256"],
              "all_words_fit": all(v["words"] <= 128 for v in results["variants"]),
              "positive_oracle": all(not v["oracle_error_kinds"] for v in (baseline, small, large)),
              "negative_late_data": "data_valid_delay" in negative["oracle_error_kinds"],
              "guard_scales_earliest_fall": all(v["timing"]["earliest_controller_fall"]["gap_ns"]
                      == baseline["timing"]["earliest_controller_fall"]["gap_ns"] + 20*v["added_clocks"]
                      for v in (small, large)),
              "speed_not_faster": all(v["fastest_ideal_hz"] <= baseline["fastest_ideal_hz"]
                                       for v in (small, large))}
    results.update({"checks": checks, "ended_utc": utc()})
    save(out / "result.json", results)
    assert all(checks.values()), checks


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
    # The pinned cocotb bootstrap discovers modules in its simulator cwd.
    # Stage the test under H: and preserve the testbench's source timestamp.
    for name in ("Makefile", "tb.v"):
        shutil.copy2(root / "test" / name, out / name)
    shutil.copy2(Path(__file__), out / "guard_screen.py")
    for name, expected in production["model_sha256"].items():
        raw = gzip.decompress((root / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" /
                               (name + ".gz")).read_bytes())
        assert sha(raw) == expected
        (out / name).write_bytes(raw)
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(Path(__file__).resolve().parent),
                   str(root / "test"), str(root)]), I2C_GENERAL_VARIANT="od128",
               I2C_GENERAL_RECORD_DIR=str(out), COUNCIL_REPO=str(root),
               PYTHONHASHSEED="0", COCOTB_RANDOM_SEED="20261124")
    sim = out / "sim"
    command = ["make", "-C", str(out), f"SRC_DIR={root/'src'}", "SIM=icarus", f"SIM_BUILD={sim}",
               "COCOTB_TEST_MODULES=guard_screen", f"COCOTB_RESULTS_FILE={out/'results.xml'}",
               "GENERAL_IO=yes", "G2_CURRENT=yes", "G2_SRAM=yes", f"SRAM_MODEL_DIR={out}",
               "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
    proc = subprocess.run(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, check=False, timeout=1200)
    (out / "run.log").write_text(proc.stdout, encoding="utf-8")
    print(proc.stdout)
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
