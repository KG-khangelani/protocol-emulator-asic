# SPDX-License-Identifier: Apache-2.0
"""Bounded proof of the actual public-loaded held-response SPI programs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from build_variants import ROOT, FILES, once
from run_formal import digest
from run_program_invariants import prepare as prepare_instrumented
from run_program_sensitivity import execute, vcd_frames, FILES_FORMAL

sys.path.insert(0, str(ROOT))
from experiments.spi_phase.four_mode_programs import image, describe
from tools.spi_four_mode_oracle import timing, assess

SPEC = ROOT / "docs/specs/spi-held-program-proof.md"


def prepare(out):
    sources = prepare_instrumented(out)
    for source, target in (("held_spi.sv", "public_spi.sv"),
                           ("held_invariants.vh", "program_invariants.vh")):
        (out / "inputs" / target).write_bytes(
            (ROOT / "experiments/spi_phase/pins" / source).read_bytes())
    return sources


def preflight(out):
    """Run actual instrumented RTL; check premises and independent pin oracle."""
    inputs = out / "inputs"
    cases = []
    for polarity in (0, 1):
        for order in (0, 1):
            for profile, tx, rx in (("early", 0x96, 0x69), ("late", 0, 255),
                                    ("jitter", 255, 0)):
                name = f"mode{2*polarity}-order{order}-{profile}"
                path = out / "preflight" / name
                path.mkdir(parents=True)
                source = (inputs / "public_spi.sv").read_text()
                source = once(source, "(* anyconst *) reg [7:0] tx_byte, rx_byte;",
                              f"wire [7:0] tx_byte=8'd{tx}, rx_byte=8'd{rx};")
                source = once(source, "(* anyconst *) reg msb_first, cpol;",
                              f"wire msb_first=1'b{order}, cpol=1'b{polarity};")
                source = once(source, "(* anyseq *) reg raw_miso, select_valid;",
                              "reg raw_miso, select_valid;")
                response = {"early": "1", "late": "24",
                            "jitter": "(m%2 ? 24 : 1)"}[profile]
                drive = f"""    reg last_raw=0;
    always @(*) begin
        raw_miso=1; select_valid=cycle[0];
        for (integer m=0;m<8;m=m+1)
            if (exec_edge>=3+50*m+{response})
                raw_miso=msb_first ? rx_byte[7-m] : rx_byte[m];
    end
    always @(posedge clk) begin
        last_raw<=raw_miso;
        if (cycle>=1 && cycle<=32 && write_index[1:0]==0)
            $display("WORD %0d %08x", write_index[4:2], load_word);
        if (cycle>=37 && cycle<=441)
            $display("TRACE %0d %0d %0d %0d %0d %0d %0d",
                previous_edge,uio_out,uio_oe,last_raw,f_rx_result,f_rx_valid,f_state);
    end
"""
                source = once(source, "    tt_um_khangelani_protocol_emulator dut(.*);",
                              drive + "    tt_um_khangelani_protocol_emulator dut(.*);")
                source = source.replace("assume(", "assert(")
                (path / "driver.sv").write_text(source)
                (path / "clock.sv").write_text(
                    "`timescale 1ns / 1ps\nmodule sim; reg clk=0; public_spi dut(clk); "
                    'initial begin repeat(445) begin #10 clk=1; #10 clk=0; end '
                    '$display("PREFLIGHT_COMPLETE"); $finish; end endmodule\n')
                command = ["iverilog", "-g2012", "-s", "sim", "-I"+str(inputs),
                           "-o", str(path/"sim.vvp")]
                command += [str(inputs/n) for n in FILES_FORMAL
                            if n.endswith(".v") and n != "public_spi.sv"]
                command += [str(path/"driver.sv"), str(path/"clock.sv")]
                compile_run = execute(command, path/"compile.log", 30)
                if compile_run["returncode"]:
                    raise RuntimeError("preflight compilation failed: "+name)
                run = execute(["vvp", str(path/"sim.vvp")], path/"run.log", 30)
                log = (path/"run.log").read_text()
                words = re.findall(r"^WORD (\d+) ([0-9a-f]{8})$", log, re.M)
                program, cs = image(polarity*2, order, "held")
                expected = describe(program)["encoded_words"]
                trace = []
                for values in re.findall(r"^TRACE ([0-9 ]+)$", log, re.M):
                    n, gpio, oe, raw, result, valid, state = map(int, values.split())
                    trace.append({"edge": n, "out": gpio, "oe": oe, "miso": raw,
                                  "rx": result, "rx_valid": valid,
                                  "state": ("RUN", "WAIT", "HALT", "FAULT")[state]})
                schedule = timing(polarity*2, cs)
                errors = assess(trace, schedule, tx, rx, order,
                                [s+24 for s in schedule["sample"]])
                ok = (run["returncode"] == 0 and "PREFLIGHT_COMPLETE" in log
                      and "ERROR:" not in log and "FATAL:" not in log
                      and words == [(str(i), word) for i, word in enumerate(expected)]
                      and not errors)
                (path/"trace.json").write_text(json.dumps(trace, separators=(",", ":"))+"\n")
                cases.append({"name": name, "mode": polarity*2, "order": order,
                              "tx": tx, "rx": rx, "profile": profile,
                              "status": "PASS" if ok else "FAIL",
                              "serialized_words_match_e0027": words == [
                                  (str(i), word) for i, word in enumerate(expected)],
                              "oracle_errors": errors[:8], "trace_sha256": digest(path/"trace.json"),
                              "compile": compile_run, "run": run})
                (out/"preflight.json").write_text(json.dumps(cases, indent=2)+"\n")
                if not ok:
                    raise RuntimeError("preflight assertions/oracle failed: "+name)
    return cases


def inspect_control(name, task, failed):
    witnesses = sorted((task/"proof/engine_0").glob("trace*.vcd"))
    rows = [r for p in witnesses for r in vcd_frames(p)]
    if name == "wrong_public_mosi":
        observations = [r for r in rows if r.get("cycle") == 40]
        ok = bool(observations) and all("public_spi.sv:" in f for f in failed)
        ok = ok and all((r["uio_out"] & 1) ==
                       ((r["tx_byte"] >> (7 if r["msb_first"] else 0)) & 1)
                       for r in observations)
        keys = ("cycle", "cpol", "msb_first", "tx_byte", "uio_out", "expected_mosi")
    else:
        observations = [r for r in rows if r.get("cycle") == 88]
        ok = bool(observations) and all("program_invariants.vh:" in f for f in failed)
        ok = ok and any(((r["f_sampled_inputs"] >> 1) & 1) !=
                       ((r["rx_byte"] >> (7 if r["msb_first"] else 0)) & 1)
                       for r in observations)
        # Preserve and check the legal first wire sample, then the bad consumed tick.
        wire = [r for r in rows if r.get("cycle") == 64]
        consumed = [r for r in rows if r.get("cycle") == 86]
        ok = ok and bool(wire) and bool(consumed)
        ok = ok and all(r["raw_miso"] ==
                       ((r["rx_byte"] >> (7 if r["msb_first"] else 0)) & 1) for r in wire)
        ok = ok and any(r["raw_miso"] !=
                       ((r["rx_byte"] >> (7 if r["msb_first"] else 0)) & 1) for r in consumed)
        observations = wire + consumed + observations
        keys = ("cycle", "exec_edge", "cpol", "msb_first", "rx_byte", "raw_miso",
                "f_sampled_inputs", "f_shift_rx_data_status")
    return {"validated": bool(ok),
            "observations": [{k: r[k] for k in keys if k in r} for r in observations],
            "witness_sha256": {str(p.relative_to(task)): digest(p) for p in witnesses}}


def formal_case(out, name, mode, depth, expected):
    task = out/name
    sources = prepare(task)
    path = task/"inputs/public_spi.sv"
    original = source = path.read_text()
    delta = None
    if name == "wrong_public_mosi":
        old = "expected_sck,1'b0,expected_mosi} : 8'd0"
        new = "expected_sck,1'b0,(previous_edge == 9'd3 ? ~expected_mosi : expected_mosi)} : 8'd0"
        delta = {"old": old, "new": new}
    elif name == "missing_first_hold":
        old = "exec_edge >= 28+50*j && exec_edge <= 53+50*j)"
        new = "exec_edge >= 28+50*j && exec_edge <= 53+50*j && (j != 0 || exec_edge == 28))"
        delta = {"old": old, "new": new}
    if delta:
        source = once(source, delta["old"], delta["new"])
        assert once(source, delta["new"], delta["old"]) == original
    path.write_text(source)
    (task/"transformation.json").write_text(json.dumps(delta, indent=2)+"\n")
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
    induction = "successful proof by k-induction" in log
    tried = re.findall(r"Trying induction in step (\d+)", log)
    check = inspect_control(name, task, failed) if expected == "FAIL" and status == "FAIL" else None
    ok = run["returncode"] == 0 and status == expected
    ok = ok and (induction if mode == "prove" else bool(failed) and bool(check) and check["validated"])
    return {"name": name, "mode": mode, "depth": depth, "expected": expected, **run,
            "status": status, "raw_status": raw, "accepted": bool(ok),
            "k_induction": induction, "induction_step": int(tried[-1]) if induction else None,
            "classification": "INCONCLUSIVE_TIMEOUT" if run["timed_out"] else
                              "EXPECTED_RESULT" if ok else "UNEXPECTED_RESULT",
            "failed_assertions": failed, "negative_trace_check": check,
            "sources": sources,
            "generated_sha256": {p.name: digest(p) for p in (task/"inputs").iterdir()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build/ output directory required")
    paths = [ROOT/"src"/n for n in FILES]
    paths += [ROOT/"experiments/spi_phase"/n for n in (
        "build_variants.py", "run_formal.py", "run_integration.py", "run_program_invariants.py",
        "run_program_sensitivity.py", "run_held_program_proof.py", "four_mode_programs.py",
        "phase_programs.py")]
    paths += list((ROOT/"experiments/spi_phase/pins").glob("*"))
    paths += [SPEC, ROOT/"tools/spi_four_mode_oracle.py", ROOT/"tools/m1_contract_model.py",
              ROOT/"tools/spi_phase_reference.py", ROOT/"tools/spi_mode0_oracle.py"]
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    sources = prepare(out/"preflight-inputs")
    result = {"status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "ACTUAL_PUBLIC_LOADED_HELD_MODE0_MODE2_PROGRAMS",
              "input_sha256": hashes, "sources": sources, "tasks": [],
              "rtl": "PRODUCTION_AND_CANDIDATE_UNCHANGED",
              "assumptions": "symbolic TX/RX/order/CPOL; raw bit at S..T inclusive; fixed public driver",
              "formal_reachability_cover": "NOT_ATTEMPTED",
              "physical_qualification": "NOT_EVALUATED"}
    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    save()
    try:
        result["preflight"] = preflight(out/"preflight-inputs")
        save()
        print("12 finite preflights and independent pin/image checks PASS", flush=True)
        if args.preflight_only:
            result["status"] = "PREFLIGHT_PASS_NOT_PROOF"
            return 0
        for name, mode, depth, expected in (
                ("held_baseline", "prove", 12, "PASS"),
                ("wrong_public_mosi", "bmc", 44, "FAIL"),
                ("missing_first_hold", "bmc", 92, "FAIL")):
            task = formal_case(out, name, mode, depth, expected)
            result["tasks"].append(task)
            save()
            print(name, task["classification"], task["status"], flush=True)
        assert hashes == {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}, "source drift"
        result["status"] = ("PROVED_HELD_MODE0_MODE2_WITH_CHECKED_CONTROLS"
                            if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED")
    except Exception as error:
        result.update(status="HARNESS_OR_TOOL_FAILURE", error=str(error))
        raise
    finally:
        save()
        print(out, flush=True)
    return 0 if result["status"] == "PROVED_HELD_MODE0_MODE2_WITH_CHECKED_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
