# SPDX-License-Identifier: Apache-2.0
"""Keep the native 19-word binary fixed and vary raw arrival phase and tie ordering."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from screen import check_trace


def cases():
    for half in (250, 1000):
        for group in (0, 20, 40):
            for phase in range(20):
                for initial in (0, 1):
                    for tie_after in (False, True):
                        events, frames = {}, []
                        select = 1001
                        for index, bit in enumerate((initial, 1-initial, initial)):
                            rising = select + 320
                            falling = rising + half
                            response = falling + half
                            last = response + half
                            aborted = index < 2
                            deselect = (falling+201)//20*20 + group + phase if aborted else last+300
                            events[select] = 2*bit
                            events[rising] = 2*bit+1
                            events[falling] = 2*bit
                            if not aborted:
                                events[response] = 2*bit+1
                                events[last] = 2*bit
                            events[deselect] = 4+2*bit
                            frames.append({"select": select, "command_sample": rising, "launch": falling,
                                           "response_sample": None if aborted else response,
                                           "final_fall": None if aborted else last, "deselect": deselect,
                                           "aborted": aborted, "bit": bit})
                            select = deselect + 160
                        yield {"kind": "candidate", "profile": "low_abort_reselect_abort", "half": half,
                               "group": group, "phase": phase, "initial": initial, "tieAfter": tie_after,
                               "events": sorted(events.items()), "frames": frames, "finish": frames[-1]["deselect"]+400}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tools", type=Path)
    parser.add_argument("hex", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if not out.is_relative_to(Path.cwd().resolve() / "build"):
        raise ValueError("output must be under build")
    out.mkdir(parents=True, exist_ok=False)
    start = datetime.now(timezone.utc).isoformat()
    words = [int(s, 16) for s in args.hex.read_text("ascii").splitlines()]
    digest = hashlib.sha256(b"".join(n.to_bytes(2,"little") for n in words)).hexdigest()
    if digest != "1ef4cfdc0a65b504aee42941c5716ee6194e79800dc927cf57ebda035cd93faf":
        raise ValueError("wrong target binary")
    tests = list(cases())
    run = subprocess.run(["node", str(HERE/"target_trace.cjs"), str(args.tools.resolve())], text=True,
                         input=json.dumps({"cases": tests, "images": {"candidate": words}}),
                         capture_output=True, check=True, timeout=50)
    observed = json.loads(run.stdout)
    if len(observed) != len(tests) or len(tests) != 480:
        raise ValueError("phase test inventory changed")
    result = {"start_utc": start, "image_sha256_le": digest, "rows": [],
              "columns": ["half_ns", "group_ns", "phase_ns", "initial_bit", "tie_after", "cold_abort_ns",
                          "post_reselect_abort_ns", "final_fall_release_ns", "errors"], "counterexample": None}
    for test, response in zip(tests, observed):
        errors, frames = check_trace(test, response["observed"])
        latencies = [f["release_latency_ns"] for f in frames]
        result["rows"].append([test["half"], test["group"], test["phase"], test["initial"], int(test["tieAfter"]),
                               *latencies, errors])
        if errors and result["counterexample"] is None:
            result["counterexample"] = {"request": test, "output_oe_and_value": response["observed"], "errors": errors}
    result["case_dispositions"] = dict(Counter("rejected" if r[-1] else "accepted" for r in result["rows"]))
    result["end_utc"] = datetime.now(timezone.utc).isoformat()
    (out/"phase.json").write_text(json.dumps(result,separators=(",",":"))+"\n", encoding="utf-8")
    print(result["case_dispositions"])
    for position in (5,6,7):
        data = [r[position] for r in result["rows"] if r[position] is not None]
        print(result["columns"][position], min(data), max(data))


if __name__ == "__main__":
    main()
