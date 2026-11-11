# SPDX-License-Identifier: Apache-2.0
"""Actual-program sensitivity controls; keep expected failures and witnesses."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import xml.etree.ElementTree as ET

from build_variants import ROOT, FILES, once
from run_formal import digest
from run_program_invariants import prepare

FILES_FORMAL = (
    "project.v", "phase_engine.v", "m1_program_store.v", "m1_data_store.v",
    "m1_input_sync.v", "public_spi.sv", "program_bindings.vh",
    "program_invariants.vh",
)


def execute(command, log_path, seconds, env=None):
    """This runner executes in Linux Docker; reap solver descendants on timeout."""
    start = time.monotonic()
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            code, timed_out = 124, True
    return {"command": command, "returncode": code, "timed_out": timed_out,
            "seconds": round(time.monotonic()-start, 3), "wall_limit": seconds}


def vcd_frames(path):
    """Read SMTBMC witnesses by top-level signal name, without simulator imports."""
    names, scopes, values, frames = {}, [], {}, []
    stamp = None
    header = True
    for line in path.read_text().splitlines():
        words = line.split()
        if header:
            if words[:1] == ["$scope"]:
                scopes.append(words[2])
            elif words[:1] == ["$upscope"]:
                scopes.pop()
            elif words[:1] == ["$var"] and scopes == ["public_spi"]:
                names[words[3]] = words[4]
            elif words[:1] == ["$enddefinitions"]:
                header = False
            continue
        if line.startswith("#"):
            if stamp is not None:
                frames.append({"time": stamp, **values})
            stamp = int(line[1:])
        elif line.startswith("b"):
            bits, code = words[0][1:], words[1]
            if code in names and set(bits) <= {"0", "1"}:
                values[names[code]] = int(bits, 2)
        elif line[:1] in ("0", "1") and line[1:] in names:
            values[names[line[1:]]] = int(line[0])
    if stamp is not None:
        frames.append({"time": stamp, **values})
    return frames


def inspect_negative(name, task_dir, failed):
    witnesses = sorted((task_dir/"proof/engine_0").glob("trace*.vcd"))
    rows = [row for p in witnesses for row in vcd_frames(p)]
    if name == "wrong_public_mosi":
        observations = [r for r in rows if r.get("cycle") == 39 and
                        "uo_out" in r and "uio_out" in r]
        ok = bool(observations) and all("public_spi.sv:" in f for f in failed)
        for row in observations:
            bit = (row["tx_byte"] >> (7 if row["msb_first"] else 0)) & 1
            ok = ok and (row["uio_out"] & 1) == bit
        keys = ("cycle", "tx_byte", "msb_first", "uio_out", "expected_mosi")
    else:
        observations = [r for r in rows if r.get("cycle") == 65 and
                        "f_sampled_inputs" in r]
        ok = bool(observations) and all("program_invariants.vh:" in f for f in failed)
        ok = ok and any(((r["f_sampled_inputs"] >> 1) & 1) !=
                       ((r["rx_byte"] >> (7 if r["msb_first"] else 0)) & 1)
                       for r in observations)
        keys = ("cycle", "rx_byte", "msb_first", "f_sampled_inputs",
                "f_shift_rx_data_status", "raw_miso")
    return {"validated": bool(ok),
            "observations": [{k: r[k] for k in keys if k in r} for r in observations],
            "witness_sha256": {str(p.relative_to(task_dir)): digest(p) for p in witnesses}}


def formal_case(out, name, mode, depth, expected, mutation=None, order=None):
    task = out/name
    sources = prepare(task)
    source_path = task/"inputs/public_spi.sv"
    source = original = source_path.read_text()
    delta = None
    if mutation == "mosi":
        old = "expected_sck,1'b0,expected_mosi} : 8'd0"
        new = "expected_sck,1'b0,(previous_edge == 9'd2 ? ~expected_mosi : expected_mosi)} : 8'd0"
        source = once(source, old, new)
        delta = {"old": old, "new": new}
    elif mutation == "premise":
        old = "&& exec_edge == 27+50*j)"
        new = "&& j != 0 && exec_edge == 27+50*j)"
        source = once(source, old, new)
        delta = {"old": old, "new": new}
    elif mode == "cover":
        source = once(source, "(* anyconst *) reg [7:0] tx_byte, rx_byte;",
                      "wire [7:0] tx_byte=8'h96, rx_byte=8'h69;")
        source = once(source, "(* anyconst *) reg msb_first;",
                      f"wire msb_first=1'b{order};")
        source = once(source, "(* anyseq *) reg raw_miso, select_valid;",
                      "reg raw_miso; wire select_valid=cycle[0];")
        drive = """    always @(*) begin
        raw_miso=1'b1;
        for (integer m=0;m<8;m=m+1)
            if (exec_edge>=27+50*m)
                raw_miso=msb_first ? rx_byte[7-m] : rx_byte[m];
    end
    always @(posedge clk)
        cover(cycle==9'd440 && uo_out==8'ha7 &&
              f_rx_result==8'h69 && f_rx_valid);
"""
        source = once(source, "    tt_um_khangelani_protocol_emulator dut(.*);",
                      drive+"    tt_um_khangelani_protocol_emulator dut(.*);")
        delta = {"public_inputs": {"tx": 150, "rx": 105, "order": order,
                 "raw_miso": "lawful preflight holds bit from R", "select_valid": "cycle parity"},
                 "cover": "cycle440, public HALT A7, actual RX69 and valid",
                 "assertions_checked_by_cover": False}
    source_path.write_text(source)
    (task/"transformation.json").write_text(json.dumps(delta, indent=2)+"\n")
    if mutation:
        assert once(source, delta["new"], delta["old"]) == original
    cfg = (f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n"
           "\n[engines]\nsmtbmc z3\n\n[script]\nread -formal -sv " +
           " ".join(n for n in FILES_FORMAL if not n.endswith(".vh")) +
           "\nprep -top public_spi\n\n[files]\n" +
           "\n".join(str(task/"inputs"/n) for n in FILES_FORMAL)+"\n")
    (task/"proof.sby").write_text(cfg)
    run = execute(["sby", "-f", "-d", str(task/"proof"), str(task/"proof.sby")],
                  task/"proof.log", 180)
    status_path = task/"proof/status"
    raw = status_path.read_text().strip() if status_path.exists() else "MISSING"
    match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw)
    status = match.group(1) if match else "MALFORMED_OR_MISSING"
    log = (task/"proof.log").read_text()
    failed = re.findall(r"Assert failed in (.+)", log)
    covers = re.findall(r"Reached cover statement in step (\d+) at (.+)", log)
    witnesses = sorted((task/"proof/engine_0").glob("trace*.vcd"))
    induction = "successful proof by k-induction" in log
    ok = run["returncode"] == 0 and status == expected
    check = None
    if mode == "prove":
        ok = ok and induction
    elif mode == "cover":
        ok = ok and len(covers) == 1 and len(witnesses) == 1
    else:
        ok = ok and bool(failed) and bool(witnesses)
        if ok:
            check = inspect_negative(name, task, failed)
            ok = check["validated"]
    return {"name": name, "mode": mode, "depth": depth, "expected": expected,
            **run, "status": status, "raw_status": raw, "accepted": bool(ok),
            "classification": "INCONCLUSIVE_TIMEOUT" if run["timed_out"] else
                              ("EXPECTED_RESULT" if ok else "UNEXPECTED_RESULT"),
            "k_induction": induction, "failed_assertions": failed,
            "covers": covers, "negative_trace_check": check, "sources": sources,
            "generated_sha256": {p.name: digest(p) for p in (task/"inputs").iterdir()},
            "witness_sha256": {str(p.relative_to(out)): digest(p) for p in witnesses}}


def simulations(out, variant):
    module_dir = out/"simulation"
    module_dir.mkdir()
    results = []
    for simulator in ("icarus", "verilator"):
        path = module_dir/simulator
        path.mkdir()
        env = dict(os.environ)
        for key in ("COCOTB_TEST_FILTER", "COCOTB_TESTCASE", "GATES", "MAKEFLAGS"):
            env.pop(key, None)
        env["SPI_PIN_RECORD_DIR"] = str(path/"records")
        env["PYTHONPATH"] = str(ROOT/"test")+os.pathsep+str(ROOT)
        command = ["make", "-C", "test", "SIM="+simulator, "SRC_DIR="+str(variant),
                   "COCOTB_TEST_MODULES=test_spi_program_controls", "COCOTB_TEST_FILTER=",
                   "PYTHONPATH="+env["PYTHONPATH"],
                   "SIM_BUILD="+str(path/"sim"), "COCOTB_RESULTS_FILE="+str(path/"results.xml"),
                   "FST=", "COCOTB_PLUSARGS=+NO_DUMP"]
        run = execute(command, path/"run.log", 180, env)
        cases = list(ET.parse(path/"results.xml").getroot().iter("testcase")) if (path/"results.xml").exists() else []
        bad = [c.get("name") for c in cases if any(c.find(k) is not None for k in ("failure", "error", "skipped"))]
        records = [json.loads(line) for line in (path/"records/cases.jsonl").read_text().splitlines()] if (path/"records/cases.jsonl").exists() else []
        expected_names = {f"{name}-{order}" for name in ("baseline", "early", "late-input") for order in (0, 1)}
        ok = (run["returncode"] == 0 and len(cases) == 1 and not bad and len(records) == 6
              and {r["case"] for r in records} == expected_names
              and sum(r["accepted"] for r in records) == 2)
        results.append({"simulator": simulator, **run, "accepted": ok,
                        "tests": len(cases), "failed_or_skipped": bad, "records": records,
                        "records_sha256": {p.name: digest(p) for p in (path/"records").glob("*")}})
        print(simulator, "PASS" if ok else "FAIL", flush=True)
    same = results[0]["records_sha256"] == results[1]["records_sha256"]
    return results, same


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--reachability-only", action="store_true")
    mode.add_argument("--simulation-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build/ output directory required")
    out.mkdir(parents=True)
    inputs = [ROOT/"src"/name for name in FILES]
    inputs += [ROOT/"experiments/spi_phase"/name for name in
               ("build_variants.py", "run_formal.py", "run_integration.py",
                "run_program_invariants.py", "run_program_sensitivity.py", "pin_timing.py")]
    inputs += list((ROOT/"experiments/spi_phase/pins").glob("*"))
    inputs += [ROOT/"docs/specs/spi-program-sensitivity.md", ROOT/"test/test_spi_mode0_pins.py", ROOT/"test/test_spi_program_controls.py",
               ROOT/"test/test.py", ROOT/"test/Makefile", ROOT/"test/tb.v"]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    result = {"status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
              "scope": ("FINITE_PUBLIC_PROGRAM_CONTROLS" if args.simulation_only else
                        "CONCRETE_TERMINAL_REACHABILITY" if args.reachability_only else
                        "ACTUAL_PUBLIC_LOADED_PROGRAM_SENSITIVITY"),
              "input_sha256": hashes, "tasks": [],
              "production_rtl_changed": False, "candidate_rtl_changed": False}
    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    save()
    try:
        configs = [("cover_lsb", "cover", 444, "PASS", None, 0),
                   ("cover_msb", "cover", 444, "PASS", None, 1)] if args.reachability_only else [
                   ("baseline", "prove", 12, "PASS", None, None),
                   ("wrong_public_mosi", "bmc", 42, "FAIL", "mosi", None),
                   ("missing_first_premise", "bmc", 72, "FAIL", "premise", None)]
        if args.simulation_only:
            configs = []
            prepare(out/"baseline")
        for name, mode, depth, expected, mutation, order in configs:
            task = formal_case(out, name, mode, depth, expected, mutation, order)
            result["tasks"].append(task)
            save()
            print(name, task["classification"], task["status"], flush=True)
        if not args.reachability_only:
            result["simulations"], result["cross_simulator_records_identical"] = simulations(
                out, out/"baseline/variants/compact/src")
        assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in inputs}, "input drift"
        passed = all(t["accepted"] for t in result["tasks"])
        if not args.reachability_only:
            passed = passed and all(s["accepted"] for s in result["simulations"])
            passed = passed and result["cross_simulator_records_identical"]
        result["status"] = ("SIMULATION_ONLY_PASS" if args.simulation_only else "PASS") if passed else "NOT_QUALIFIED"
    except Exception as error:
        result.update(status="HARNESS_OR_TOOL_FAILURE", error=str(error))
        raise
    finally:
        save()
        print(out, flush=True)
    return 0 if result["status"] in ("PASS", "SIMULATION_ONLY_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
