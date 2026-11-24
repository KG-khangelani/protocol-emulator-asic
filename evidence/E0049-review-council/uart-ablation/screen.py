# SPDX-License-Identifier: Apache-2.0
"""Compare the released two-frame UART programs with counted manual shifts."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd().resolve()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from assembler import assemble, load_plan
from production_sram import verify
from tools.uart_rx_host_service import HostReader


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check(condition, message):
    if not condition:
        raise ValueError(message)


def build_fixture(out):
    profile = json.loads((ROOT / "tools/production-profile.json").read_bytes())
    sources = [ROOT / name for name in profile["files_sha256"] if name.endswith(".v")]
    for name, digest in profile["model_sha256"].items():
        src = ROOT / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" / (name + ".gz")
        model = gzip.decompress(src.read_bytes())
        check(sha(model) == digest, name)
        (out / name).write_bytes(model)
        sources.append(out / name)
    args = ["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-s", "uart_tb",
            "-o", str(out / "bench.vvp"), str(HERE / "uart_tb.sv"), *map(str, sources)]
    process = subprocess.run(args, capture_output=True, text=True, timeout=45)
    (out / "compile.log").write_text(process.stdout + process.stderr)
    process.check_returncode()


def plan(source, dest):
    image = assemble(source)
    rows = []
    for step in load_plan(image)["steps"]:
        expected = step["expected"]
        # Only payload data varies across cases. The fixture changes both the actual
        # write byte and the expected public readback, at these four tagged rows.
        slot = {"write_TX0": 1, "read_TX0": 1, "write_TX1": 2, "read_TX1": 2}.get(step["action"], 0)
        rows.append("{} {} {} {:02x} {:02x} {:02x} {} {:02x} {} {:02x} {}".format(
            step["rst_n"], step["ena"], int(step["host_drives_uio"]), step["ui_in"],
            step["uio_in"], expected["uio_oe"], int("uio_out" in expected),
            expected.get("uio_out", 0), int("uo_out" in expected), expected.get("uo_out", 0), slot))
    dest.write_text("\n".join(rows) + "\n")
    return {"words": len(image["words"]), "binary_sha256": image["binary_sha256"],
            "load_steps": len(rows)}


def case_list(period, receive, negative):
    if negative:
        return [(150, 105, 1, 0, 0)]
    if period == 4:
        rows = [(a, a ^ 255, a % 4, 0, int(receive and a == 150)) for a in range(256)]
    else:
        rows = [(a, a ^ 255, p, 0, int(receive and a == 150 and p == 1))
                for a in (0, 85, 150, 255) for p in range(4)]
    if receive:
        rows.extend((150, 105, 1, bad, 1) for bad in (1, 2, 3))
    return rows


def inspect(trace, cases, period, receive, manual, negative):
    lines = trace.splitlines()
    failures = [line for line in lines if line.startswith("MISMATCH ")]
    if negative:
        check(len(failures) == 1, "mutation escaped the wire checker")
        reason = failures[0].split()[1]
        check(reason in ("wire", "direction", "valid", "raw"), failures)
        return {"expected_checker_rejection": failures[0]}
    check(not failures, failures)
    check(f"DONE {len(cases)}" in lines, "incomplete simulation")
    results = [list(map(int, line.split()[1:])) for line in lines if line.startswith("CASE ")]
    check(len(results) == len(cases), "missing results")
    witnesses = {}
    for line in lines:
        if line.startswith("OBS "):
            idx, edge, status, valid, raw = map(int, line.split()[1:])
            witnesses.setdefault(idx, {})[edge] = status, valid, raw
    host = []
    for row, inputs in zip(results, cases):
        idx, a, b, phase, bad, end, status, observed = row
        check((a, b, phase, bad) == inputs[:4], "different public input")
        if not (receive and inputs[4]):
            continue
        reader = HostReader(period, period, 1, 1)
        for n in range(1, observed + 1):
            if n in witnesses[idx]:
                value = witnesses[idx][n]
            requests = reader.requests(n)
            reader.observe(n, requests, value[0], value[1], value[2])
        if bad or manual:
            check(reader.rejected and reader.accepted is None and reader.first is None,
                  "released host incorrectly delivered")
        else:
            check(reader.accepted == (a, b), "released host failed on its original image")
        host.append({"case": idx, "bad": bad, "terminal": f"{status:02x}", "edge": end,
                     "delivered": reader.accepted, "rejected": reader.rejected})
    return {"cases": len(results), "runtime_edges_checked": sum(row[-1] for row in results),
            "terminal_edges": sorted({row[-3] for row in results}),
            "terminal_status_hex": sorted({f"{row[-2]:02x}" for row in results}), "host": host}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="new directory under build/")
    out = parser.parse_args().out.resolve()
    check(out.is_relative_to(ROOT / "build"), "output outside build")
    out.mkdir(parents=True, exist_ok=False)
    verify(ROOT)
    build_fixture(out)
    result = {"schema": "council-uart-ablation-v1", "inputs": {}, "groups": {}, "unmet": []}
    for filename in ("manual_tx.asm", "manual_rx.asm", "uart_tb.sv", "screen.py"):
        result["inputs"][filename] = sha((HERE / filename).read_bytes())
    versions = subprocess.run(["iverilog", "-V"], capture_output=True, text=True)
    result["simulator"] = versions.stdout.splitlines()[0]
    for direction in ("tx", "rx"):
        receive = direction == "rx"
        original = ROOT / "programs/od128-sram-v1" / ("uart_" + direction + ".asm")
        sources = {"released": original.read_text(), "manual": (HERE / ("manual_" + direction + ".asm")).read_text()}
        sources["late"] = sources["manual"].replace("cycles=PERIOD-3", "cycles=PERIOD-2", 1)
        if not receive:
            sources["wrong-slot"] = sources["manual"].replace("payload=TX1", "payload=TX0")
        for variant, source in sources.items():
            negative = variant in ("late", "wrong-slot")
            for period in (4, 434):
                key = f"{direction}-{variant}-{period}"
                rows = case_list(period, receive, negative)
                plan_path, cases_path = out / (key + ".plan"), out / (key + ".cases")
                group = plan(source.replace(".const PERIOD 434", f".const PERIOD {period}"), plan_path)
                result["groups"][key] = group
                cases_path.write_text("".join(" ".join(map(str, row)) + "\n" for row in rows))
                command = ["vvp", str(out / "bench.vvp"), f"+plan={plan_path}",
                           f"+steps={group['load_steps']}", f"+cases={cases_path}", f"+period={period}",
                           f"+rx={int(receive)}", f"+manual={int(variant != 'released')}"]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
                trace = proc.stdout + proc.stderr
                (out / (key + ".log")).write_text(trace)
                try:
                    check(proc.returncode == 0, "simulator error: " + trace[-250:])
                    group.update(inspect(trace, rows, period, receive, variant != "released", negative))
                except ValueError as exc:
                    group["unmet"] = str(exc)
                    result["unmet"].append(key)
                print(key, group.get("unmet", group.get("expected_checker_rejection", "pass")), flush=True)
                (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return int(bool(result["unmet"]))


if __name__ == "__main__":
    sys.exit(main())
