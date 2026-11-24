# SPDX-License-Identifier: Apache-2.0
"""Build and score a one-bit externally clocked target with stalled-clock abort/reselect."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def compile_images(tool_root, out, image):
    source = (HERE / "echo.pio").read_text("ascii")
    variants = {"candidate": source, "ignore_cs": source.replace("jmp pin release", "nop"),
                "stale_value": source.replace("    out pins, 1", "    set pins, 1"),
                "false_reset": source.replace("jmp !x rise_loop", "jmp !x release")}
    images = {}
    for name, assembly in variants.items():
        (out / (name + ".pio")).write_text(assembly, encoding="ascii")
        if os.name == "nt":
            cmd = ["docker", "run", "--rm", "--pull=never", "--read-only", "--network", "none",
                   "--mount", f"type=bind,source={tool_root},target=/tools,readonly",
                   "--mount", f"type=bind,source={out},target=/work", "-w", "/work", image, "/tools/pioasm"]
        else:
            cmd = [str(tool_root / "pioasm")]
        subprocess.run([*cmd, "-o", "hex", name + ".pio", name + ".hex"], check=True, cwd=out, timeout=30)
        words = [int(v, 16) for v in (out / (name + ".hex")).read_text("ascii").splitlines()]
        if not 1 <= len(words) <= 32:
            raise ValueError("program does not fit one PIO")
        images[name] = words
    return images


def make_test(kind, profile, half, phase, offset):
    # Inputs are a requester schedule in real ns. Their generation uses no PIO
    # program counter, state-machine output, simulator register or output transition.
    events = {}
    frames = []
    start = 1000 + phase
    for index, bit in enumerate((1, 0)):
        rising = start + 320
        falling = rising + half
        aborted = profile in ("abort", "high_abort") and index == 0
        response_rise = falling + half + (2000 if profile == "pause" and index == 0 else 0)
        final_fall = response_rise + half
        end = falling + 201 + offset if aborted else final_fall + 300
        if profile == "high_abort" and index == 0:
            end = response_rise + 201
        events[start] = 2 * bit
        events[rising] = 2 * bit + 1
        events[falling] = 2 * bit
        if not aborted:
            events[response_rise] = 2 * bit + 1
            events[final_fall] = 2 * bit
        events[end] = 4 + 2 * bit
        if profile == "high_abort" and index == 0:
            events[response_rise] = 2 * bit + 1
            events[end] = 4 + 2 * bit + 1
            events[end + 600] = 4 + 2 * bit
        frames.append({"select": start, "command_sample": rising, "launch": falling,
                       "response_sample": response_rise if not aborted else None,
                       "final_fall": final_fall if not aborted else None, "deselect": end,
                       "aborted": aborted, "bit": bit})
        start = end + (900 if profile == "high_abort" else 160 if aborted else 500)
    return {"kind": kind, "profile": profile, "half": half, "phase": phase, "offset": offset,
            "events": sorted(events.items()), "frames": frames, "finish": frames[-1]["deselect"] + 400}


def tests():
    for half in (1000, 500, 250):
        for phase in (1, 7, 13, 19):
            for profile, offsets in (("normal", [0]), ("pause", [0]), ("abort", [0, 20, 40])):
                control = {"normal": "stale_value", "pause": "false_reset", "abort": "ignore_cs"}[profile]
                for offset in offsets:
                    for kind in ("candidate", control):
                        yield make_test(kind, profile, half, phase, offset)
    for phase in (1, 19):
        yield make_test("candidate", "high_abort", 1000, phase, 0)


def check_trace(test, edges):
    def at(ns):
        return next(value for when, value in reversed(edges) if when <= ns)

    def stable(lo, hi, level):
        return at(lo) == level and at(hi) == level and all(v == level for t, v in edges if lo < t <= hi)

    errors = []
    summaries = []
    for n, frame in enumerate(test["frames"]):
        start, launch = frame["select"], frame["launch"]
        value = frame["bit"] + 1
        prefix = "first" if n == 0 else "reselect"
        if not stable(start, launch - 1, 0):
            errors.append(prefix + "_prefix_drive")
        if frame["aborted"]:
            reference = frame["deselect"]
            if at(reference - 1) != value:
                errors.append("abort_not_active")
        else:
            response = frame["response_sample"]
            reference = frame["final_fall"]
            if not stable(response - 60, response + 40, value):
                errors.append(prefix + "_reply")
            if not stable(response - 60, reference - 1, value):
                errors.append(prefix + "_hold")
            if test["profile"] == "pause" and n == 0 and not stable(launch + 200, response, value):
                errors.append("false_reset_in_pause")
        release = next((t for t, v in edges if t >= reference and v == 0), None)
        latency = release - reference if release is not None else None
        if latency is None or latency > 160 or at(reference - 1) != value:
            errors.append("abort_release" if frame["aborted"] else prefix + "_normal_release")
        summaries.append({"frame": prefix, "release_reference_ns": reference, "release_latency_ns": latency,
                          "sampled_output_code": at(frame["response_sample"]) if not frame["aborted"] else None})
    return sorted(set(errors)), summaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--image", default="protocol-emulator-asic-workbench:2026-07-29")
    args = parser.parse_args()
    tool_root, out = args.tools.resolve(), args.out.resolve()
    if not out.is_relative_to(Path.cwd().resolve() / "build"):
        raise ValueError("output must be in the checkout build directory")
    out.mkdir(parents=True, exist_ok=False)
    result = {"started_utc": utc(), "sources": {p: hashlib.sha256((HERE/p).read_bytes()).hexdigest()
              for p in ("echo.pio", "screen.py", "target_trace.cjs", "declaration.md", "recovery.md")},
              "node": subprocess.check_output(["node", "--version"], text=True).strip(), "observations": [], "failures": []}
    images = compile_images(tool_root, out, args.image)
    result["images"] = {k: {"words": len(v), "sha256_le": hashlib.sha256(
                        b"".join(n.to_bytes(2, "little") for n in v)).hexdigest()} for k, v in images.items()}
    submitted = list(tests())
    submitted[0]["retainHost"] = True
    run = subprocess.run(["node", str(HERE/"target_trace.cjs"), str(tool_root)], input=json.dumps(
        {"cases": submitted, "images": images}), text=True, capture_output=True, timeout=45)
    if run.returncode:
        (out / "emulator-error.log").write_text(run.stderr, encoding="utf-8")
        raise ValueError(run.stderr[-800:])
    all_observed = json.loads(run.stdout)
    if len(all_observed) != len(submitted):
        raise ValueError("incomplete external requester test")
    for test, measured in zip(submitted, all_observed):
        errors, frames = check_trace(test, measured["observed"])
        required = {"ignore_cs": "abort_release", "stale_value": "reselect_reply", "false_reset": "false_reset_in_pause"}
        expected = not errors if test["kind"] == "candidate" else required[test["kind"]] in errors
        if test["profile"] == "high_abort":
            expected = errors == ["abort_release"]
        record = {k: test[k] for k in ("kind", "profile", "half", "phase", "offset")}
        record.update({"errors": errors, "frames": frames, "setup_mmio": measured["setup"], "public_oe_value_edges": measured["observed"]})
        result["observations"].append(record)
        if not expected:
            result["failures"].append({"case": {k: test[k] for k in ("kind", "profile", "half", "phase", "offset")}, "errors": errors})
        if measured["operations"]:
            result["one_host_transcript"] = measured["operations"]
    result["case_counts"] = dict(Counter(x["kind"] for x in submitted))
    result["ended_utc"] = utc()
    (out/"result.json").write_text(json.dumps(result, separators=(",", ":"))+"\n",encoding="utf-8")
    print(result["case_counts"], "unexpected", len(result["failures"]), result["failures"][:2])
    return int(bool(result["failures"]))


if __name__ == "__main__":
    sys.exit(main())
