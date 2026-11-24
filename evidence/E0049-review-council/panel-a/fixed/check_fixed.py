# SPDX-License-Identifier: Apache-2.0
"""Compare a fixed controller against the council's frozen DS18B20 operation."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
ONEWIRE = ROOT / "evidence/E0049-review-council/onewire"
TOP = "tt_um_khangelani_protocol_emulator"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def process(args, cwd):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=120)


def record_run(args, cwd, log):
    result = process(args, cwd)
    (cwd / log).write_text(result.stdout + result.stderr, encoding="utf-8")
    return result


def events_relative_to_reset(obs, key):
    return [edge - obs["falls"][0] for edge in obs[key]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new directory under repository build/")
    out = parser.parse_args().out.resolve()
    if not out.is_relative_to(ROOT / "build"):
        raise ValueError("output must be under build/")
    out.mkdir(parents=True, exist_ok=False)
    os.environ["TMPDIR"] = str(out)
    spec = importlib.util.spec_from_file_location("onewire_judging", ONEWIRE / "screen.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    reference = json.loads((ONEWIRE / "result.json").read_text(encoding="utf-8"))
    source = (HERE / "fixed_power_query.v").read_text(encoding="utf-8")
    variants = {
        "normal": source,
        "bad-command": source.replace("16'hb4cc", "16'hb4cd"),
        "short-reset": source.replace("15'd25000", "15'd20000"),
    }
    if len(set(variants.values())) != 3:
        raise ValueError("one of the fixed implementation mutations was ineffective")

    # One reset and two public inhibit edges. The external target and result
    # checker below use the same pins and ownership definitions as the chair.
    bootstrap = ["0 1 0 01 00 00 1 01 1 20", "1 1 0 01 00 00 1 01 1 20",
                 "1 1 0 01 00 00 1 01 1 20"]
    (out / "fixed.plan").write_text("\n".join(bootstrap) + "\n", encoding="ascii")
    result = {
        "schema": "council-fixed-onewire-v1", "started_utc": timestamp(),
        "simulator": process(["iverilog", "-V"], out).stdout.splitlines()[0],
        "synthesis_tool": process(["yosys", "-V"], out).stdout.strip(),
        "fixed_attempt_inputs_sha256": {
            path.name: digest(path) for path in
            [HERE / "fixed_power_query.v", Path(__file__).resolve(), HERE / "fixed-declaration.md",
             ONEWIRE / "contract.md", ONEWIRE / "power_query_tb.sv", ONEWIRE / "screen.py",
             ONEWIRE / "result.json", out / "fixed.plan"]
        },
        "host": {"preparation_rising_edges": len(bootstrap), "initialization": "reset, inhibit, inhibit",
                 "start_transition": "lower ui_in[0] before first active edge, ena remains high",
                 "runtime_host_actions": 0, "program_upload_bytes": 0,
                 "cmd_bits_fixed_in_logic": 16, "post_fabrication_reprogramming": False},
        "cases": {}, "unmet": [],
    }
    for name, content in variants.items():
        (out / (name + ".v")).write_text(content, encoding="utf-8")
        check = record_run(["iverilog", "-g2012", "-s", "power_query_tb", "-o", name + ".vvp",
                            str(ONEWIRE / "power_query_tb.sv"), name + ".v"],
                           out, name + ".compile.log")
        check.check_returncode()

    for name, version, delay, width, stuck, parasite, expected, rejection in oracle.cases():
        sim = record_run(["vvp", version + ".vvp", "+plan=fixed.plan", "+steps=3",
                          f"+delay={delay}", f"+width={width}", f"+stuck={stuck}",
                          f"+parasite={parasite}"], out, name + ".log")
        row = {"sim_exit": sim.returncode, "expected_rejection": rejection}
        try:
            oracle.check(sim.returncode == 0, "simulator failure")
            obs = oracle.inspect(sim.stdout + sim.stderr)
            row["observed"] = obs
            base = reference["cases"][name]["observed"]
            row["aligned_vs_vm"] = {
                "first_drive_edge_delta": obs["falls"][0] - base["falls"][0],
                "fall_offsets_equal": events_relative_to_reset(obs, "falls") == events_relative_to_reset(base, "falls"),
                "release_offsets_equal": events_relative_to_reset(obs, "releases") == events_relative_to_reset(base, "releases"),
                "terminal_offset_delta_edges": (obs["halt_edge"] - obs["falls"][0]) - (base["halt_edge"] - base["falls"][0]),
            }
            oracle.judge(obs, len(bootstrap), expected)
            reason = None
        except ValueError as exc:
            reason = str(exc)
        row["observed_rejection"] = reason
        if reason != rejection:
            result["unmet"].append(name)
        result["cases"][name] = row

    result["digital_ended_utc"] = timestamp()
    (out / "functional.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    synth_script = f"read_verilog normal.v; synth -noabc -top {TOP}; tee -o generic-stat.json stat -json"
    result["generic_synthesis_command"] = ["yosys", "-Q", "-T", "-p", synth_script]
    synth = record_run(result["generic_synthesis_command"], out, "yosys.log")
    synth.check_returncode()
    stats = json.loads((out / "generic-stat.json").read_text(encoding="utf-8"))
    result["fixed_generic_stat"] = stats["modules"]["\\" + TOP]
    result["ended_utc"] = timestamp()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{len(result['cases'])} cases, {len(result['unmet'])} unexpected: {result['unmet']}")
    return int(bool(result["unmet"]))


if __name__ == "__main__":
    sys.exit(main())
