# SPDX-License-Identifier: Apache-2.0
"""Run the council's frozen public-pin power query. Run from the repository root."""
import argparse
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT / "tools"))
from assembler import assemble, load_plan
from production_sram import verify


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, reason):
    if not condition:
        raise ValueError(reason)


def run(command, timeout=60):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def make_plan(source, dest):
    image = assemble(source)
    plan = load_plan(image)
    rows = []
    for step in plan["steps"]:
        expected = step["expected"]
        rows.append("{} {} {} {:02x} {:02x} {:02x} {} {:02x} {} {:02x}".format(
            step["rst_n"], step["ena"], int(step["host_drives_uio"]), step["ui_in"],
            step["uio_in"], expected["uio_oe"], int("uio_out" in expected),
            expected.get("uio_out", 0), int("uo_out" in expected), expected.get("uo_out", 0)))
    dest.write_text("\n".join(rows) + "\n", encoding="ascii")
    return {"words": len(image["words"]), "binary_sha256": image["binary_sha256"],
            "bytes": len(image["words"]) * 4, "load_steps": len(rows)}


def compile_fixture(out):
    lock = json.loads((ROOT / "tools/production-profile.json").read_bytes())
    sources = [ROOT / name for name in lock["files_sha256"] if name.endswith(".v")]
    for name, digest in lock["model_sha256"].items():
        path = ROOT / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" / (name + ".gz")
        model = gzip.decompress(path.read_bytes())
        check(sha(model) == digest, "SRAM model identity " + name)
        (out / name).write_bytes(model)
        sources.append(out / name)
    command = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-s", "power_query_tb",
               "-o", str(out / "bench.vvp"), str(HERE / "power_query_tb.sv"), *map(str, sources)]
    result = run(command)
    (out / "compile.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    result.check_returncode()


def inspect(trace):
    events = {"LOAD": [], "DRIVE": [], "WIREBIT": [], "HALT": []}
    for line in trace.splitlines():
        fields = line.split()
        if fields and fields[0] in events:
            events[fields[0]].append([int(value) for value in fields[1:]])
    check(len(events["HALT"]) == len(events["LOAD"]) == 1, "missing load or terminal event")
    drives = events["DRIVE"]
    check(drives and len(drives) % 2 == 0, "incomplete DQ pulses")
    check([value for _, value in drives] == [1, 0] * (len(drives) // 2), "invalid drive order")
    falls = [n for n, _ in drives[::2]]
    releases = [n for n, _ in drives[1::2]]
    bits = events["WIREBIT"]
    check([i for i, _ in bits] == list(range(len(bits))), "write sample order")
    check(all(bit in (0, 1) for _, bit in bits), "nonbinary target samples")
    commands = [sum(bit << i for i, (_, bit) in enumerate(bits[j:j+8]))
                for j in range(0, len(bits), 8)]
    halt, marker = events["HALT"][0]
    return {"load_steps": events["LOAD"][0][0], "falls": falls, "releases": releases,
            "decoded_wire_bytes": commands, "write_samples": len(bits),
            "halt_edge": halt, "result": marker}


def judge(obs, steps, expected):
    # Wire expectations below are independent of the image, assembler, PC and target state.
    falls, releases = obs["falls"], obs["releases"]
    widths = [r - f for r, f in zip(releases, falls)]
    check(obs["load_steps"] == steps and obs["halt_edge"] <= 125000, "load or time cap")
    check(abs(widths[0] - 25000) <= 1, "reset duration")
    if expected == 3:
        check(len(falls) == 1 and obs["write_samples"] == 0, "commands after failed presence")
    else:
        check(obs["write_samples"] == 16 and obs["decoded_wire_bytes"] == [0xCC, 0xB4],
              "command bytes")
        check(len(falls) == 18, "pulse count")
        check(abs(falls[1] - releases[0] - 25000) <= 1, "reset recovery")
        check(all(abs(b - a - 3500) <= 1 for a, b in zip(falls[1:], falls[2:])),
              "slot period")
        golden = [300 if byte & (1 << i) else 3100 for byte in (0xCC, 0xB4) for i in range(8)]
        check(all(abs(actual - wanted) <= 1 for actual, wanted in zip(widths[1:], golden)),
              "write low duration")
        check(abs(widths[-1] - 300) <= 1 and obs["halt_edge"] - falls[-1] >= 3000,
              "read slot duration")
    check(obs["result"] == expected, "terminal power result")


def cases():
    for delay, width, parasite in itertools.product((15, 60), (60, 240), (0, 1)):
        yield f"present-{delay}-{width}-{parasite}", "normal", delay, width, 0, parasite, 1 + parasite, None
    yield "absent", "normal", 0, 0, 0, 0, 3, None
    yield "stuck", "normal", 0, 0, 1, 0, 3, None
    yield "bad-command", "bad-command", 15, 60, 0, 0, 1, "command bytes"
    yield "short-reset", "short-reset", 15, 60, 0, 0, 1, "reset duration"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="fresh directory under build/")
    out = parser.parse_args().out.resolve()
    check(out.is_relative_to(ROOT / "build"), "output must be under build/")
    out.mkdir(parents=True, exist_ok=False)
    verify(ROOT)
    compile_fixture(out)
    normal = (HERE / "power_query.asm").read_text(encoding="utf-8")
    prefix, command_text = normal.split("; Skip ROM,", 1)
    flipped = command_text.replace("cycles=LONG\n", "cycles=SHORT\n", 1)
    flipped = flipped.replace("cycles=LONG_RECOVERY\n", "cycles=SHORT_RECOVERY\n", 1)
    sources = {"normal": normal, "bad-command": prefix + "; Skip ROM," + flipped,
               "short-reset": normal.replace("cycles=24998", "cycles=19998", 1)}
    images = {name: make_plan(source, out / (name + ".plan")) for name, source in sources.items()}
    check(len({image["binary_sha256"] for image in images.values()}) == 3, "ineffective mutations")

    result = {"schema": "council-onewire-screen-v1", "images": images, "cases": {},
              "input_sha256": {name: sha((HERE / name).read_bytes())
                               for name in ("power_query.asm", "power_query_tb.sv", "screen.py")},
              "simulator": run(["iverilog", "-V"]).stdout.splitlines()[0]}
    failures = []
    for name, source, delay, width, stuck, parasite, expected, rejection in cases():
        steps = images[source]["load_steps"]
        command = ["vvp", str(out / "bench.vvp"), "+plan=" + str(out / (source + ".plan")),
                   f"+steps={steps}", f"+delay={delay}", f"+width={width}", f"+stuck={stuck}",
                   f"+parasite={parasite}"]
        sim = run(command)
        trace = sim.stdout + sim.stderr
        (out / (name + ".log")).write_text(trace, encoding="utf-8")
        row = {"simulator_exit": sim.returncode, "expected_result": expected,
               "expected_checker_rejection": rejection}
        result["cases"][name] = row
        try:
            check(sim.returncode == 0, "simulator failure")
            row["observed"] = inspect(trace)
            judge(row["observed"], steps, expected)
            reason = None
        except ValueError as error:
            reason = str(error)
        row["checker_rejection"] = reason
        if reason != rejection:
            failures.append(name)
    result["unmet_cases"] = failures
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{len(result['cases'])} cases, {len(failures)} unmet: {failures}")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
