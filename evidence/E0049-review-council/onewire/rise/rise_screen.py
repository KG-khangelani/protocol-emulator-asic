# SPDX-License-Identifier: Apache-2.0
"""Replay the power query on the unmodified RTL with two delayed digital receivers."""
import argparse
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd().resolve()
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / "evidence/E0049-review-council/onewire"
sys.path.insert(0, str(ORIGINAL))
from screen import check, make_plan, verify


def rise_ticks(cap_pf, threshold):
    # R in ohms, C in picofarads, divided by the 20,000 ps clock period.
    return math.ceil(-4700 * cap_pf * math.log1p(-threshold / 3.3) / 20000)


def candidate(source):
    edits = [(".const SHORT 298", ".const SHORT 98"),
             (".const SHORT_RECOVERY 3198", ".const SHORT_RECOVERY 3398"),
             ("cycles=3498", "cycles=3648"), ("cycles=21497", "cycles=21347"),
             ("cycles=398\n    WAIT_PIN", "cycles=598\n    WAIT_PIN")]
    for before, after in edits:
        check(source.count(before) == 1, "missing unique source edit " + before)
        source = source.replace(before, after)
    return source


def compile_sim(out):
    profile = json.loads((ROOT / "tools/production-profile.json").read_bytes())
    paths = [ROOT / name for name in profile["files_sha256"] if name.endswith(".v")]
    for name, digest in profile["model_sha256"].items():
        path = ROOT / "evidence/E0042-sram-prefetch-screen/feasibility/verilog" / (name + ".gz")
        data = gzip.decompress(path.read_bytes())
        check(hashlib.sha256(data).hexdigest() == digest, name)
        (out / name).write_bytes(data)
        paths.append(out / name)
    subprocess.run(["iverilog", "-g2012", "-DFUNCTIONAL", "-DSYNTHESIS", "-s", "rise_peer",
                    "-o", str(out / "bench.vvp"), str(HERE / "rise_peer.sv"), *map(str, paths)],
                   check=True, timeout=45)


def run_case(out, name, image, cap, parasite, delay, width, sample, golden_falls):
    remote_ticks = rise_ticks(cap, 3.0 if parasite else 2.2)
    local_ticks = rise_ticks(cap, 2.31)
    cmd = ["vvp", str(out / "bench.vvp"), f"+plan={out / (name + '.plan')}",
           f"+steps={image['load_steps']}", f"+remote={remote_ticks}", f"+local={local_ticks}",
           f"+delay={delay*50}", f"+width={width*50}", f"+sample={sample*50}", f"+parasite={parasite}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=25, check=True)
    trace = proc.stdout + proc.stderr
    tag = f"{name}-{cap}-{parasite}-{delay}-{width}-{sample}"
    (out / (tag + ".log")).write_text(trace)
    ends = [s.split()[1:] for s in trace.splitlines() if s.startswith("RESULT ")]
    check(len(ends) == 1, "missing terminal " + tag)
    n, marker, word, seen, presence, _end, slots, recovery = ends[0]
    n, marker, seen, slots, recovery = map(int, (n, marker, seen, slots, recovery))
    received = int(word, 16)
    falls = [int(s.split()[1]) for s in trace.splitlines() if s.startswith("DRIVE ") and s.endswith(" 1")]
    check(falls == golden_falls[:len(falls)], "commanded fall schedule " + tag)
    if marker == 3 and seen == 0:
        outcome = "missed-presence"
    elif slots != 17 or seen != 16:
        outcome = "missing-sensed-slot"
    elif received != 0xB4CC:
        outcome = "wrong-received-command"
    elif marker != 1 + parasite:
        outcome = "wrong-power-result"
    elif recovery < 50:
        outcome = "short-sensed-recovery"
    elif abs(n - 109503) > 1:
        outcome = "schedule-mismatch"
    else:
        outcome = "accepted"
    return {"image": name, "capacitance_pF": cap, "parasite": parasite, "presence_delay_us": delay,
            "presence_width_us": width, "write_sample_us": sample, "remote_rise_ticks": remote_ticks,
            "controller_rise_ticks": local_ticks, "presence_start_after_release_ticks": int(presence),
            "sensed_slots": slots, "sampled_writes": seen, "received_lsb_first_words_hex": f"{received:04x}",
            "minimum_sensed_recovery_ticks": recovery if slots > 1 else None,
            "terminal_edge": n, "marker": marker, "judgment": outcome}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    out = parser.parse_args().out.resolve()
    check(out.is_relative_to(ROOT / "build"), "fresh build directory required")
    out.mkdir(parents=True, exist_ok=False)
    verify(ROOT)
    compile_sim(out)
    original = (ORIGINAL / "power_query.asm").read_text()
    golden = json.loads((ORIGINAL / "result.json").read_bytes())["cases"]["present-15-60-0"]["observed"]
    results = {"schema": "council-sensed-edge-v1", "images": {}, "in_envelope": [], "stress": []}
    for name, source in (("original", original), ("retimed", candidate(original))):
        info = make_plan(source, out / (name + ".plan"))
        check(info["words"] == 85 and info["load_steps"] == 712, "unexpected image size")
        results["images"][name] = info
        for cap, parasite, delay, width, sample in itertools.product((100, 1000), (0, 1),
                                                                     (15, 60), (60, 240), (15, 60)):
            row = run_case(out, name, info, cap, parasite, delay, width, sample, golden["falls"])
            results["in_envelope"].append(row)
        results["stress"].append(run_case(out, name, info, 2200, 1, 15, 60, 15, golden["falls"]))
        results["stress"].append(run_case(out, name, info, 2200, 1, 60, 60, 60, golden["falls"]))
        accepted = sum(r["image"] == name and r["judgment"] == "accepted" for r in results["in_envelope"])
        print(f"{name}: {accepted}/32 accepted", flush=True)
        info["accepted"] = accepted
        info["decision_for_entire_declared_envelope"] = "PASS" if accepted == 32 else "REJECT"
        (out / "result.json").write_text(json.dumps(results, indent=2) + "\n")
    small = [r for r in results["in_envelope"] if r["capacitance_pF"] == 100 or not r["parasite"]]
    check(all(r["judgment"] == "accepted" for r in small), "control environment changed")
    check(any(r["judgment"] == "missed-presence" for r in results["in_envelope"]), "missing stress effect")
    return 0


if __name__ == "__main__":
    sys.exit(main())
