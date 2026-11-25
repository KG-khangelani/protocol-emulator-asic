# SPDX-License-Identifier: Apache-2.0
"""Check the timing and terminal markers using the retained independent public-pin RTL fixture."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.remote_onewire.program import COUNCIL, source
from tools.cold_load import fresh_directory, prepare_models
from tools.production_sram import verify
sys.path.insert(0, str(COUNCIL))
from screen import cases, inspect, make_plan


def score(obs, marker):
    falls, rises = obs["falls"], obs["releases"]
    if rises[0] - falls[0] != 6250:
        return "reset duration"
    if marker != 3:
        if obs["decoded_wire_bytes"] != [0xcc, 0xb4] or obs["write_samples"] != 16 or len(falls) != 18:
            return "command bytes"
        bits = [(byte >> bit) & 1 for byte in (0xcc, 0xb4) for bit in range(8)]
        if [rise - fall for rise, fall in zip(rises[1:], falls[1:])] != [25 if b else 775 for b in bits] + [25]:
            return "write or read low width"
        if any(b - a != 950 for a, b in zip(falls[1:], falls[2:])) or obs["halt_edge"] - falls[-1] < 750:
            return "slot timing"
    elif len(falls) != 1 or obs["write_samples"] != 0:
        return "unexpected command after error"
    return None if obs["result"] == marker else "terminal marker"


def run(out):
    profile = verify(ROOT)
    models = prepare_models(out, profile)
    sv = (COUNCIL / "power_query_tb.sv").read_text()
    for old, new in (("#9 clk", "#39 clk"), ("#10 clk", "#40 clk"), ("== 1500", "== 375"),
                     ("start_us * 50", "start_us * 25 / 2"), ("(start_us + width_us) * 50", "(start_us + width_us) * 25 / 2"),
                     ("age >= 500 && age < 2250", "age >= 125 && age < 562"), ("chip_oe[2:0] !== 3'b110", "chip_oe[3:0] !== 4'b1100"),
                     ("pins[2:1]", "pins[3:2]")):
        if sv.count(old) != 1:
            raise ValueError(old)
        sv = sv.replace(old, new)
    fixture = out / "bench.sv"
    fixture.write_text(sv)
    sources = [ROOT / "src" / name for name in profile["source_sha256"]]
    sources.extend(models / name for name in profile["model_sha256"])
    command = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-s", "power_query_tb", "-o", "bench.vvp",
               str(fixture), *map(str, sources)]
    with (out / "compile.log").open("w") as stream:
        subprocess.run(command, cwd=out, stdout=stream, stderr=subprocess.STDOUT, timeout=45, check=True)
    images = {variant: make_plan(source(variant), out / (variant + ".plan"))
              for variant in ("normal", "short-reset", "bad-command")}
    rows = {}
    for name, variant, delay, width, stuck, parasite, marker, rejection in cases():
        cmd = ["vvp", "bench.vvp", f"+plan={variant}.plan", f"+steps={images[variant]['load_steps']}",
               f"+delay={delay}", f"+width={width}", f"+stuck={stuck}", f"+parasite={parasite}"]
        result = subprocess.run(cmd, cwd=out, capture_output=True, text=True, timeout=30)
        log = result.stdout + result.stderr
        (out / (name + ".log")).write_text(log)
        result.check_returncode()
        obs = inspect(log)
        actual = score(obs, marker)
        rows[name] = dict(observed=obs, expected_marker=marker, expected_rejection=rejection, actual_rejection=actual)
    ok = all(r["actual_rejection"] == r["expected_rejection"] for r in rows.values())
    version = subprocess.check_output(["iverilog", "-V"], text=True, stderr=subprocess.STDOUT).splitlines()[0]
    record = dict(status="PASS" if ok else "FAIL", core_hz=12_500_000, images=images, cases=rows,
                  profile_sha256=profile["profile_sha256"], compiler=version)
    (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(record["status"], images["normal"], [(k, v["actual_rejection"]) for k, v in rows.items()])
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    run(fresh_directory(parser.parse_args().out))
