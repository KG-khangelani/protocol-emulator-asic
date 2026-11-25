"""Run one candidate through the frozen public SPI fixture and retain the actual pins."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
ROOT = PARENT.parents[1]
sys.path[:0] = [str(PARENT), str(ROOT)]
from requester import matrix
from stress import assess, extra_cases
from run import (ARCHIVE, ARCHIVE_SHA, NETLIST_SHA, PDK_FILES, REPRESENTATIVE, checked,
                 digest, make_plan, parse_pin_log)
from selector_orders import memory_file
from tools.cold_load import fresh_directory, prepare_models
from tools.production_sram import verify


def stamp():
    return datetime.now(timezone.utc).isoformat()


def json_gz(path, data):
    raw = (json.dumps(data, separators=(",", ":")) + "\n").encode()
    path.write_bytes(gzip.compress(raw, mtime=0))


def prepare_sim(out, pdk, verilator=False):
    production = verify(ROOT)
    models = prepare_models(out, production)
    sources = [ROOT / "src" / name for name in production["source_sha256"]]
    if pdk:
        archive = ROOT / ARCHIVE
        checked(archive.read_bytes(), ARCHIVE_SHA, ARCHIVE)
        netlist = out / "submitted.v"
        with ZipFile(archive) as zipped:
            data = zipped.read("tt_submission/tt_um_khangelani_protocol_emulator.v")
        netlist.write_bytes(checked(data, NETLIST_SHA, "submitted functional netlist"))
        sources = [netlist]
        for name, wanted in PDK_FILES.items():
            checked((pdk / name).read_bytes(), wanted, name)
            sources.append(pdk / name)
    inputs = ["-DFUNCTIONAL", "-DSYNTHESIS", "-DSIM", PARENT / "target_tb.sv", *sources, *sorted(models.glob("*.v"))]
    if verilator:
        obj = out / "verilated"
        with (out / "verilator-build.log").open("w") as log:
            subprocess.run(["verilator", "--binary", "--timing", "-j", "2", "-Wno-fatal", "--top-module",
                            "target_tb", "--Mdir", obj, *inputs], stdout=log, stderr=subprocess.STDOUT, check=True)
        command = [obj / "Vtarget_tb"]
    else:
        executable = out / "target.vvp"
        subprocess.run(["iverilog", "-g2012", "-s", "target_tb", "-o", executable, *inputs], check=True)
        command = ["vvp", executable]
    return command, production["profile_sha256"]


def baseline():
    cases = json.loads(gzip.decompress((ROOT / "evidence/E0055-spi-target-comparison/cases.json.gz").read_bytes()))
    if json.loads(json.dumps(dict(matrix()))) != cases or len(cases) != 736:
        raise ValueError("baseline requester differs from E0055")
    return cases


def observe(name, case, events, command, plan, steps):
    events.write_text("".join(f"{t} {v}\n" for t, v in case["events"]), encoding="ascii")
    args = [*command, f"+plan={plan}", f"+rows={steps}", f"+events={events}",
            f"+count={len(case['events'])}", f"+finish={case['finish']}"]
    result = subprocess.run(args, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise ValueError(f"{name}: {result.stdout[-600:]} {result.stderr[-600:]}")
    return parse_pin_log(result.stdout, case, steps)


def run(out, firmware, cases, pdk, workers, verilator=False):
    started = stamp()
    (out / "events").mkdir()
    text = firmware.read_text(encoding="utf-8")
    info = make_plan(ROOT, text, out, "target")
    command, profile = prepare_sim(out, pdk, verilator)
    steps = info["clocked_load_steps"]
    # Parallel runs share the same immutable compiled model and loader plan.
    # A RAM copy avoids rereading a 15 MB gate model across the Docker mount for each trial.
    with ExitStack() as files:
        plan = files.enter_context(memory_file("watchdog.plan", (out / "target.plan").read_bytes()))
        if command[0] == "vvp":
            command = ["vvp", files.enter_context(memory_file("watchdog.vvp", command[1].read_bytes()))]
        def trial(item):
            name, case = item
            return name, observe(name, case, out / "events" / name, command, plan, steps)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            traces = dict(pool.map(trial, cases.items()))
    json_gz(out / "pins.json.gz", traces)
    results = {n: assess(n, c, traces[n]) for n, c in cases.items()}
    errors = {n: r["errors"] for n, r in results.items() if r["errors"]}
    backend = "verilator-rtl" if verilator else "submitted-netlist" if pdk else "production-rtl"
    version = ["verilator", "--version"] if verilator else ["iverilog", "-V"]
    report = dict(started_utc=started, ended_utc=stamp(), backend=backend,
                  simulator=subprocess.check_output(version, stderr=subprocess.DEVNULL,
                                                    text=True).splitlines()[0],
                  production_profile_sha256=profile, source_sha256=digest(text.encode()),
                  assembler_sha256=digest((out / "release-assembler.py").read_bytes()), image=info,
                  case_count=len(cases), failures=len(errors), first_failure=next(iter(errors.items()), None))
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(report["backend"], info["words"], "words,", len(cases) - len(errors), "/", len(cases),
          "passed.", "First failure:", str(report["first_failure"])[:280], flush=True)
    return not errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    backend = parser.add_mutually_exclusive_group()
    backend.add_argument("--pdk", type=Path, help="run the submitted netlist with these verified cell models")
    backend.add_argument("--verilator", action="store_true", help="run production RTL through Verilator")
    parser.add_argument("--firmware", type=Path, default=HERE / "target.asm")
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 17))
    parser.add_argument("--smoke", action="store_true", help="use the fifteen prespecified cross-checks")
    parser.add_argument("--stress", action="store_true", help="use the additional phase, boundary and abort sweeps")
    args = parser.parse_args()
    cases = dict(extra_cases()) if args.stress else baseline()
    if args.smoke:
        if args.stress:
            parser.error("choose either the baseline smoke test or the stress sweep")
        cases = {name: cases[name] for name in REPRESENTATIVE}
    if not run(fresh_directory(args.out), args.firmware, cases, args.pdk, args.workers, args.verilator):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
