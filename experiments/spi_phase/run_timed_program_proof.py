# SPDX-License-Identifier: Apache-2.0
"""Induction of actual eight-word mode1/3 programs and checked counterexamples."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

from build_variants import ROOT, FILES, once
from build_timed_gpio import timed_engine
from run_integration import readouts
from run_formal import digest
from run_program_invariants import prepare as prepare_instrumented
from run_program_sensitivity import execute, vcd_frames, FILES_FORMAL

sys.path.insert(0, str(ROOT))
from experiments.spi_phase.timed_gpio_programs import image, encode
from tools.spi_four_mode_oracle import timing, assess

SPEC = ROOT / "docs/specs/spi-timed-gpio-comparison.md"


def prepare(out, variant):
    sources = prepare_instrumented(out)
    inputs=out/"inputs"
    engine=timed_engine((inputs/"phase_engine.v").read_text(encoding="utf-8"),variant)
    if variant=="F":
        extras=[("formal_gpio_pending",1),("formal_gpio_pending_value",8),("formal_gpio_pending_oe",8)]
        ports=", ".join("output wire "+(f"[{w-1}:0] " if w>1 else "")+n for n,w in extras)
        engine=readouts(engine,[
            ("output wire formal_phase_active, output wire formal_phase_prepared\n",
             "output wire formal_phase_active, output wire formal_phase_prepared, "+ports+"\n"),
            ("    reg gpio_pending;", "    reg gpio_pending;\n"),
            ("    reg [7:0] gpio_pending_value, gpio_pending_oe;",
             "    reg [7:0] gpio_pending_value, gpio_pending_oe;\n"+
             "".join(f"    assign {n}={n.removeprefix('formal_')};\n" for n,w in extras))
        ],"timed-engine-readouts.v",inputs)
        top=(inputs/"project.v").read_text(encoding="utf-8")
        top=readouts(top,[
            ("    wire engine_rst_n =", "".join("    wire "+(f"[{w-1}:0] " if w>1 else "")+n+";\n" for n,w in extras)+"    wire engine_rst_n ="),
            ("input wire clk, input wire rst_n,", "input wire clk, input wire rst_n,\n"+
             ",\n".join("    output wire "+(f"[{w-1}:0] " if w>1 else "")+"f_"+n for n,w in extras)+","),
            (".formal_phase_prepared(formal_phase_prepared)\n",
             ".formal_phase_prepared(formal_phase_prepared), "+", ".join(f".{n}({n})" for n,w in extras)+"\n"),
            ("\nendmodule", "".join(f"\n    assign f_{n}={n};" for n,w in extras)+"\nendmodule")
        ],"timed-top-readouts.v",inputs)
        (inputs/"project.v").write_text(top)
        with (inputs/"program_bindings.vh").open("a") as f:
            f.write("".join("wire "+(f"[{w-1}:0] " if w>1 else "")+"f_"+n+";\n" for n,w in extras))
    (inputs/"phase_engine.v").write_text(engine)
    for source,target in (("timed_spi.sv","public_spi.sv"),("timed_invariants.vh","program_invariants.vh")):
        text=(ROOT/"experiments/spi_phase/pins"/source).read_text(encoding="utf-8")
        if variant=="F": text="`define VARIANT_F\n"+text
        (inputs/target).write_text(text)
    return sources


def preflight(out, variant):
    """Run actual instrumented RTL; check premises and independent pin oracle."""
    inputs = out / "inputs"
    cases = []
    for polarity in (0, 1):
        for order in (0, 1):
            for profile, tx, rx in (("early", 0x96, 0x69), ("late", 0, 255),
                                    ("jitter", 255, 0)):
                name = f"mode{2*polarity+1}-order{order}-{profile}"
                path = out / "preflight" / name
                path.mkdir(parents=True)
                source = (inputs / "public_spi.sv").read_text(encoding="utf-8")
                source = once(source, "(* anyconst *) reg [7:0] tx_byte, rx_byte;",
                              f"wire [7:0] tx_byte=8'd{tx}, rx_byte=8'd{rx};")
                source = once(source, "(* anyconst *) reg msb_first, cpol;",
                              f"wire msb_first=1'b{order}, cpol=1'b{polarity};")
                source = once(source, "(* anyseq *) reg raw_miso, select_valid;",
                              "reg raw_miso, select_valid;")
                response = {"early": "1", "late": "96",
                            "jitter": "(m%2 ? 96 : 1)"}[profile]
                drive = f"""    reg last_raw=0;
    always @(*) begin
        raw_miso=1; select_valid=cycle[0];
        for (integer m=0;m<8;m=m+1)
            if (exec_edge>=27+50*m+(({response}+3)/4))
                raw_miso=msb_first ? rx_byte[7-m] : rx_byte[m];
    end
    always @(posedge clk) begin
        last_raw<=raw_miso;
        if (cycle>=1 && cycle<=32 && write_index[1:0]==0)
            $display("WORD %0d %08x", write_index[4:2], load_word);
        if (cycle>=37 && cycle<=465)
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
                    'initial begin repeat(469) begin #10 clk=1; #10 clk=0; end '
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
                log = (path/"run.log").read_text(encoding="utf-8")
                words = re.findall(r"^WORD (\d+) ([0-9a-f]{8})$", log, re.M)
                program = image(variant,polarity*2+1,order)
                cs=2
                expected = [f"{encode(w,variant):08x}" for w in program]
                trace = []
                for values in re.findall(r"^TRACE ([0-9 ]+)$", log, re.M):
                    n, gpio, oe, raw, result, valid, state = map(int, values.split())
                    trace.append({"edge": n, "out": gpio, "oe": oe, "miso": raw,
                                  "rx": result, "rx_valid": valid,
                                  "state": ("RUN", "WAIT", "HALT", "FAULT")[state]})
                schedule = timing(polarity*2+1, cs)
                errors = assess(trace, schedule, tx, rx, order,
                                [s+24 for s in schedule["sample"]])
                ok = (run["returncode"] == 0 and "PREFLIGHT_COMPLETE" in log
                      and "ERROR:" not in log and "FATAL:" not in log
                      and words == [(str(i), word) for i, word in enumerate(expected)]
                      and not errors)
                (path/"trace.json").write_text(json.dumps(trace, separators=(",", ":"))+"\n")
                cases.append({"name": name, "mode": polarity*2+1, "order": order,
                              "tx": tx, "rx": rx, "profile": profile,
                              "status": "PASS" if ok else "FAIL",
                              "serialized_words_match_timed_model": words == [
                                  (str(i), word) for i, word in enumerate(expected)],
                              "oracle_errors": errors[:8], "trace_sha256": digest(path/"trace.json"),
                              "compile": compile_run, "run": run})
                (out/"preflight.json").write_text(json.dumps(cases, indent=2)+"\n")
                if not ok:
                    raise RuntimeError("preflight assertions/oracle failed: "+name)
    return cases


def inspect_control(name, task, failed):
    witnesses=sorted((task/"proof/engine_0").glob("trace*.vcd"))
    rows=[r for p in witnesses for r in vcd_frames(p)]
    if name=="wrong_public_mosi":
        observations=[r for r in rows if r.get("cycle")==64 and "uio_out" in r]
        ok=bool(observations) and all("public_spi.sv:" in f for f in failed)
        ok=ok and all((r["uio_out"]&1)==((r["tx_byte"]>>(7 if r["msb_first"] else 0))&1) for r in observations)
    else:
        wire=[r for r in rows if r.get("exec_edge")==52 and "raw_miso" in r]
        consumed=[r for r in rows if r.get("exec_edge")==74 and "raw_miso" in r]
        sampled=[r for r in rows if r.get("exec_edge")==76 and "f_sampled_inputs" in r]
        bit=lambda r:(r["rx_byte"]>>(7 if r["msb_first"] else 0))&1
        ok=bool(wire and consumed and sampled) and all("program_invariants.vh:" in f for f in failed)
        ok=ok and all(r["raw_miso"]==bit(r) for r in wire)
        ok=ok and any(r["raw_miso"]!=bit(r) for r in consumed)
        ok=ok and any(((r["f_sampled_inputs"]>>1)&1)!=bit(r) for r in sampled)
        observations=wire+consumed+sampled
    keys=("cycle","exec_edge","cpol","msb_first","tx_byte","rx_byte","uio_out","raw_miso","f_sampled_inputs")
    return {"validated":bool(ok),"observations":[{k:r[k] for k in keys if k in r} for r in observations],
            "witness_sha256":{str(p.relative_to(task)):digest(p) for p in witnesses}}


def formal_case(out, name, mode, depth, expected, variant):
    task = out/name
    sources = prepare(task,variant)
    path = task/"inputs/public_spi.sv"
    original = source = path.read_text(encoding="utf-8")
    delta = None
    if name == "wrong_public_mosi":
        old = "expected_sck,1'b0,expected_mosi} : 8'd0"
        new = "expected_sck,1'b0,(previous_edge == 9'd27 ? ~expected_mosi : expected_mosi)} : 8'd0"
        delta = {"old": old, "new": new}
    elif name == "missing_first_hold":
        old = "exec_edge >= 52+50*j && exec_edge <= 77+50*j)"
        new = "exec_edge >= 52+50*j && exec_edge <= 77+50*j && (j != 0 || exec_edge == 52))"
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
    raw = status_path.read_text(encoding="utf-8").strip() if status_path.exists() else "MISSING"
    match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw)
    status = match.group(1) if match else "MALFORMED_OR_MISSING"
    log = (task/"proof.log").read_text(encoding="utf-8")
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
    parser.add_argument("--variant",choices=("P","F"),required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/"build").resolve()):
        raise ValueError("new isolated build/ output directory required")
    paths = [ROOT/"src"/n for n in FILES]
    paths += [ROOT/"experiments/spi_phase"/n for n in (
        "build_variants.py", "run_formal.py", "run_integration.py", "run_program_invariants.py",
        "run_program_sensitivity.py", "run_timed_program_proof.py", "build_timed_gpio.py", "timed_gpio_programs.py", "four_mode_programs.py",
        "phase_programs.py")]
    paths += list((ROOT/"experiments/spi_phase/pins").glob("*"))
    paths += [SPEC, ROOT/"tools/spi_four_mode_oracle.py", ROOT/"tools/m1_contract_model.py",
              ROOT/"tools/spi_phase_reference.py", ROOT/"tools/spi_mode0_oracle.py"]
    hashes = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
    sources = prepare(out/"preflight-inputs",args.variant)
    result = {"status": "RUNNING", "started_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "ACTUAL_PUBLIC_LOADED_TIMED_MODE1_MODE3_PROGRAMS", "variant":args.variant,
              "input_sha256": hashes, "sources": sources, "tasks": [],
              "rtl": "ISOLATED_TIMED_CANDIDATE_PRODUCTION_UNCHANGED",
              "assumptions": "symbolic TX/RX/order/CPOL; raw bit at S..T inclusive; fixed public driver",
              "formal_reachability_cover": "NOT_ATTEMPTED",
              "physical_qualification": "NOT_EVALUATED"}
    def save():
        (out/"result.json").write_text(json.dumps(result, indent=2)+"\n")
    save()
    try:
        result["preflight"] = preflight(out/"preflight-inputs",args.variant)
        save()
        print("12 finite preflights and independent pin/image checks PASS", flush=True)
        if args.preflight_only:
            result["status"] = "PREFLIGHT_PASS_NOT_PROOF"
            return 0
        for name, mode, depth, expected in (
                ("timed_baseline", "prove", 12, "PASS"),
                ("wrong_public_mosi", "bmc", 128, "FAIL"),
                ("missing_first_hold", "bmc", 128, "FAIL")):
            task = formal_case(out, name, mode, depth, expected,args.variant)
            result["tasks"].append(task)
            save()
            print(name, task["classification"], task["status"], flush=True)
        assert hashes == {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}, "source drift"
        result["status"] = ("PROVED_TIMED_MODE1_MODE3_WITH_CHECKED_CONTROLS"
                            if all(t["accepted"] for t in result["tasks"]) else "NOT_QUALIFIED")
    except Exception as error:
        result.update(status="HARNESS_OR_TOOL_FAILURE", error=str(error))
        raise
    finally:
        save()
        print(out, flush=True)
    return 0 if result["status"] == "PROVED_TIMED_MODE1_MODE3_WITH_CHECKED_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
