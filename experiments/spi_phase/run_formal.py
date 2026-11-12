# SPDX-License-Identifier: Apache-2.0
"""Isolated phase assertions/refinement; retain every SBY attempt and witness."""

import argparse
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from build_variants import ROOT, build, once
from legacy_baseline import BASELINE, baseline_inputs

PORTS = {
    "pc": 5, "state": 2, "wait_left": 16, "gpio_value": 8, "gpio_oe": 8,
    "wait_is_input_status": 1, "wait_pin_status": 3, "wait_level_status": 1,
    "wait_timeout_skip_status": 1, "wait_is_shift_status": 1,
    "loop_active_status": 1, "loop_remaining_status": 8, "loop_start_status": 5,
    "loop_end_status": 5, "shift_active_status": 1, "shift_bits_done_status": 3,
    "shift_msb_first_status": 1, "shift_tx_pin_status": 3, "shift_rx_pin_status": 3,
    "shift_tx_data_status": 8, "shift_rx_data_status": 8, "shift_burst_status": 1,
    "shift_period_status": 16, "shift_tx_slot_status": 1, "shift_result_write": 1,
    "shift_result_data": 8,
}
DERIVED = {"wait_is_shift_status", "shift_burst_status", "shift_result_write", "shift_result_data"}
INPUTS = ("clk", "rst_n", "ena", "instruction", "instruction_valid", "sampled_inputs", "tx_payload", "tx_payload_alt")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def declarations(prefix=""):
    return "\n".join("wire " + (f"[{width-1}:0] " if width > 1 else "") + prefix + name + ";"
                     for name, width in PORTS.items()) + "\n"


def instance(module, name, prefix="", phase=False):
    ports = [f".{p}({p})" for p in INPUTS] + [f".{p}({prefix+p})" for p in PORTS]
    if phase:
        ports += [".formal_phase_active(formal_phase_active)", ".formal_phase_prepared(formal_phase_prepared)"]
    return f"{module} {name} (" + ",\n".join(ports) + ");\n"


def vector(label, names, widths):
    return f"wire [{sum(widths)-1}:0] {label} = {{" + ",".join(names) + "};\n"


def instrument(source):
    original = source
    source = once(source, "module m1_engine #", "module phase_engine #")
    source = once(source, "    output wire shift_result_write, output wire [7:0] shift_result_data\n",
                  "    output wire shift_result_write, output wire [7:0] shift_result_data,\n"
                  "    output wire formal_phase_active, output wire formal_phase_prepared\n")
    source = once(source, "    reg phase_active;", "    assign formal_phase_active = phase_active;\n"
                  "    assign formal_phase_prepared = phase_prepared;\n    reg phase_active;")
    # Prove mechanically that instrumentation is only a rename and two readouts.
    restored = source.replace("module phase_engine #", "module m1_engine #", 1)
    restored = restored.replace("shift_result_data,\n    output wire formal_phase_active, output wire formal_phase_prepared\n",
                                "shift_result_data\n", 1)
    restored = restored.replace("    assign formal_phase_active = phase_active;\n    assign formal_phase_prepared = phase_prepared;\n", "", 1)
    assert restored == original
    return source


def prepare(output):
    manifests = build(output / "variants")
    candidate = (output / "variants/compact/src/m1_engine.v").read_text()
    proof = output / "inputs"
    proof.mkdir()
    engine = instrument(candidate)
    (proof / "phase_engine.v").write_text(engine)
    original = (BASELINE / "m1_engine.v").read_text()
    (proof / "legacy_engine.v").write_text(once(original, "module m1_engine (", "module legacy_engine ("))
    patch = difflib.unified_diff(candidate.splitlines(True), engine.splitlines(True),
                                 fromfile="compact/m1_engine.v", tofile="formal/phase_engine.v")
    (proof / "instrumentation.patch").write_text("".join(patch))
    state_names = [name for name in PORTS if name not in DERIVED]
    state_widths = [PORTS[n] for n in state_names]
    assert sum(state_widths) == 108
    header = declarations() + "wire formal_phase_active, formal_phase_prepared;\n"
    header += instance("phase_engine", "dut", phase=True)
    header += vector("all_state", state_names + ["formal_phase_active", "formal_phase_prepared"], state_widths + [1, 1])
    latched = [n for n in state_names if n not in {"pc", "state", "wait_left"}]
    header += vector("phase_latched_state", latched + ["formal_phase_active", "formal_phase_prepared"],
                     [PORTS[n] for n in latched] + [1, 1])
    (proof / "phase_bindings.vh").write_text(header)
    legacy = declarations("c_") + declarations("l_") + "wire formal_phase_active, formal_phase_prepared;\n"
    legacy += instance("phase_engine", "candidate", "c_", True) + instance("legacy_engine", "legacy", "l_")
    for label, prefix in (("candidate_outputs", "c_"), ("legacy_outputs", "l_")):
        legacy += vector(label, [prefix+n for n in PORTS], list(PORTS.values()))
    (proof / "legacy_bindings.vh").write_text(legacy)
    for name in ("phase_properties.sv", "legacy_refinement.sv"):
        (proof / name).write_bytes((ROOT / "experiments/spi_phase/formal" / name).read_bytes())
    mutations = {
        "decrement2": ("wait_left <= wait_left - 16'd1;\n                        else\n                            capture_phase_sample();",
                       "wait_left <= wait_left - 16'd2;\n                        else\n                            capture_phase_sample();"),
        "commit7": ("(phase_delay == 16'd0) && (shift_bits_done == 3'd7)",
                    "(phase_delay == 16'd0) && (shift_bits_done == 3'd6)"),
    }
    for name, (old, new) in mutations.items():
        (proof / (name + ".v")).write_text(once(engine, old, new))
    return manifests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--tasks", nargs="+", default=["phase_prove", "legacy_prove", "phase_cover", "legacy_cover", "decrement2", "commit7"])
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = (args.output or ROOT / "build/spi-phase-formal" / stamp).resolve()
    if output.exists() or not output.is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated output under build/ required")
    sources = prepare(output)
    inputs = list((ROOT / "experiments/spi_phase").glob("*.py")) + list((ROOT / "experiments/spi_phase/formal").glob("*.sv"))
    inputs += [ROOT / "docs/specs/spi-phase-formal.md", ROOT / "docs/specs/spi-phase-comparison.md"] + baseline_inputs()
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in inputs}
    generated = {str(p.relative_to(output)): digest(p) for p in (output / "inputs").iterdir()}
    record = {"status": "RUNNING", "rung": "EXPERIMENTAL_EXECUTOR_FORMAL", "input_sha256": hashes,
              "generated_sha256": generated, "sources": sources, "tasks": [],
              "assumptions": {"safety": ["first sampled edge rst_n=0; all subsequent inputs unrestricted"],
                              "legacy": ["same initial reset; exclude new phase types only at enabled valid legacy RUN fetch"],
                              "fairness": "none", "sampled_inputs": "arbitrary synchronized digital bits; no CDC model"},
              "phase_delay_bits": 16, "instrumentation": "module rename and two output readouts; inverse transform checked"}
    config = {"phase_prove": ("prove", 8, "phase_properties", "phase_engine.v", "PASS"),
              "legacy_prove": ("prove", 12, "legacy_refinement", "phase_engine.v", "PASS"),
              "phase_cover": ("cover", 40, "phase_properties", "phase_engine.v", "PASS"),
              "legacy_cover": ("cover", 40, "legacy_refinement", "phase_engine.v", "PASS"),
              "decrement2": ("bmc", 8, "phase_properties", "decrement2.v", "FAIL"),
              "commit7": ("bmc", 20, "phase_properties", "commit7.v", "FAIL")}

    def save():
        (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    save()
    try:
        for task in args.tasks:
            mode, depth, top, engine, expected = config[task]
            proof = output / "inputs"
            files = [proof / engine, proof / (top + ".sv"), proof / ("phase_bindings.vh" if top == "phase_properties" else "legacy_bindings.vh")]
            if top == "legacy_refinement":
                files.append(proof / "legacy_engine.v")
            script = "read -formal " + engine + " " + ("legacy_engine.v " if top == "legacy_refinement" else "") + top + ".sv\nprep -top " + top
            sby = f"[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n{script}\n\n[files]\n" + "\n".join(str(p) for p in files) + "\n"
            config_path = output / (task + ".sby")
            config_path.write_text(sby)
            command = ["sby", "-f", "-d", str(output / task), str(config_path)]
            started = time.monotonic()
            with (output / (task + ".log")).open("w") as log:
                try:
                    code = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300).returncode
                except subprocess.TimeoutExpired:
                    code = 124
            status_path = output / task / "status"
            raw_status = status_path.read_text().strip() if status_path.exists() else "MISSING"
            match = re.fullmatch(r"(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}", raw_status)
            status = match.group(1) if match else "MALFORMED_OR_MISSING"
            log_text = (output / (task + ".log")).read_text()
            witnesses = sorted(str(p.relative_to(output)) for p in (output / task / "engine_0").glob("trace*.vcd"))
            induction = "successful proof by k-induction" in log_text
            induction_tries = re.findall(r"Trying induction in step (\d+)", log_text)
            base_steps = re.findall(r"Checking assertions in step (\d+)", log_text)
            reached = [{"step": int(step), "location": location} for step, location in
                       re.findall(r"Reached cover statement in step (\d+) at (.+)", log_text)]
            failed = re.findall(r"Assert failed in (.+)", log_text)
            item = {"name": task, "mode": mode, "depth": depth, "engine": "smtbmc z3", "command": command,
                    "returncode": code, "status": status, "raw_status": raw_status, "expected": expected,
                    "k_induction": induction, "induction_step": int(induction_tries[-1]) if induction else None,
                    "last_checked_step": max(map(int, base_steps)) if base_steps else None,
                    "reached_covers": reached, "failed_assertions": failed,
                    "witnesses": witnesses, "seconds": round(time.monotonic()-started, 3)}
            record["tasks"].append(item)
            save()
            print(task, status, "expected", expected, flush=True)
            if code != 0 or status != expected:
                raise RuntimeError(f"{task}: {status}, exit {code}; inspect retained logs/witnesses")
            if mode == "prove" and not induction:
                raise RuntimeError("missing successful k-induction result")
            if mode in ("cover", "bmc") and not witnesses:
                raise RuntimeError("missing cover/counterexample witness")
            if mode == "cover" and len(reached) != (10 if top == "phase_properties" else 3):
                raise RuntimeError("missing cover obligation")
            if mode == "bmc" and not failed:
                raise RuntimeError("expected mutation lacks a failing assertion")
        assert hashes == {str(p.relative_to(ROOT)): digest(p) for p in inputs}
        record["status"] = "PASS"
    except Exception as error:
        record.update(status="FAIL", error=str(error))
        raise
    finally:
        save()
        print(output, flush=True)


if __name__ == "__main__":
    main()
