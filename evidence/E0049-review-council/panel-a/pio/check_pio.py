# SPDX-License-Identifier: Apache-2.0
"""Assemble and execute the bounded RP2040 PIO power query using H: scratch."""
import argparse
from collections import Counter
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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def assemble(tools, out, stem, image):
    if os.name == "nt":
        cmd = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--read-only",
               "--mount", f"type=bind,source={tools},target=/pt,readonly",
               "--mount", f"type=bind,source={out},target=/out", "-w", "/out", image, "/pt/pioasm"]
    else:
        cmd = [str(tools / "pioasm")]
    proc = subprocess.run([*cmd, "-o", "hex", stem + ".pio", stem + ".hex"], cwd=out,
                          text=True, capture_output=True, timeout=40)
    (out / (stem + ".asm.log")).write_text(proc.stdout + proc.stderr, encoding="utf-8")
    proc.check_returncode()
    words = [int(x, 16) for x in (out / (stem + ".hex")).read_text(encoding="ascii").splitlines()]
    binary = b"".join(word.to_bytes(2, "little") for word in words)
    return {"words": len(words), "bytes": len(binary), "little_endian_sha256": sha(binary)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    args = parser.parse_args()
    tools, out = args.tools.resolve(), args.out.resolve()
    if not out.is_relative_to(ROOT / "build"):
        raise ValueError("output must be under the checkout build directory")
    out.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("onewire_judging", ONEWIRE / "screen.py")
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    baseline = json.loads((ONEWIRE / "result.json").read_bytes())
    source = (HERE / "power_query.pio").read_text(encoding="utf-8")
    mutated = source.replace("set x, 30                 side 1 [3]", "set x, 23                 side 1 [15]")
    if mutated == source:
        raise ValueError("ineffective short-reset control")
    tool_record = json.loads((tools / "tools.json").read_bytes())
    result = {"schema": "council-pio-onewire-v1", "started_utc": stamp(), "cases": {}, "unmet": [],
              "host_node": subprocess.check_output(["node", "--version"], text=True).strip(),
              "assembler_archive": tool_record["assembler_archive"],
              "emulator_archive": tool_record["emulator_archive"],
              "input_sha256": {p.name: sha(p.read_bytes()) for p in
                               [HERE / "power_query.pio", HERE / "pio_trace.cjs", Path(__file__),
                                HERE / "pio-declaration.md", HERE / "pio-host-note.md",
                                ONEWIRE / "screen.py", ONEWIRE / "contract.md", ONEWIRE / "result.json"]}}
    result["images"] = {}
    for stem, contents in (("normal", source), ("short-reset", mutated)):
        (out / (stem + ".pio")).write_text(contents, encoding="ascii")
        result["images"][stem] = assemble(tools, out, stem, args.image)
    if result["images"]["normal"]["words"] != 32 or result["images"]["normal"] == result["images"]["short-reset"]:
        raise ValueError("invalid program fit or mutation")
    host_counts = None
    for name, image, delay, width, stuck, parasite, expected, rejection in oracle.cases():
        stem = "short-reset" if image == "short-reset" else "normal"
        command = "b4cd" if image == "bad-command" else "b4cc"
        command_line = ["node", str(HERE / "pio_trace.cjs"), str(tools), str(out / (stem + ".hex")),
                        str(delay), str(width), str(stuck), str(parasite), command, "0"]
        run = subprocess.run(command_line, capture_output=True, text=True, timeout=15)
        raw = run.stdout + run.stderr
        (out / (name + ".log")).write_text(raw, encoding="utf-8")
        row = {"process_exit": run.returncode, "intended_rejection": rejection}
        try:
            oracle.check(run.returncode == 0, "emulator/fixture failure")
            operations = json.loads(next(line[5:] for line in raw.splitlines() if line.startswith("HOST ")))
            counts = dict(Counter(entry[0] for entry in operations))
            if host_counts is None:
                host_counts = counts
                (out / "host-operations.json").write_text(json.dumps(operations) + "\n", encoding="utf-8")
            oracle.check(counts == host_counts and counts["readback_words"] == 32, "host operation counts")
            oracle.check("HOLD 500" in raw, "terminal hold")
            obs = oracle.inspect(raw)
            row["observed"] = obs
            base = baseline["cases"][name]["observed"]
            row["aligned_vs_vm"] = {
                "first_drive_edge_delta": obs["falls"][0] - base["falls"][0],
                "terminal_offset_delta_edges": ((obs["halt_edge"] - obs["falls"][0])
                                                - (base["halt_edge"] - base["falls"][0])),
                "all_falls_equal": [e - obs["falls"][0] for e in obs["falls"]]
                                  == [e - base["falls"][0] for e in base["falls"]],
                "all_releases_equal": [e - obs["falls"][0] for e in obs["releases"]]
                                     == [e - base["falls"][0] for e in base["releases"]]}
            oracle.judge(obs, len(operations) - counts["enable_sm"], expected)
            reason = None
        except (ValueError, StopIteration) as exc:
            reason = str(exc)
        row["observed_rejection"] = reason
        result["cases"][name] = row
        if reason != rejection:
            result["unmet"].append(name)
    result["public_mmio_operation_counts"] = host_counts
    bad = subprocess.run(["node", str(HERE / "pio_trace.cjs"), str(tools), str(out / "normal.hex"),
                          "15", "60", "0", "0", "b4cc", "1"], text=True, capture_output=True, timeout=15)
    (out / "corrupt-write.log").write_text(bad.stdout + bad.stderr, encoding="utf-8")
    result["corrupt_write"] = {"process_exit": bad.returncode,
                               "location0_detected_before_launch": bad.returncode == 12 and
                               "READBACK_MISMATCH 0" in bad.stdout and "LOAD" not in bad.stdout}
    if not result["corrupt_write"]["location0_detected_before_launch"]:
        result["unmet"].append("corrupt-write")
    result["ended_utc"] = stamp()
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{len(result['cases'])} operation cases plus corrupt upload, unmet: {result['unmet']}")
    return int(bool(result["unmet"]))


if __name__ == "__main__":
    sys.exit(main())
