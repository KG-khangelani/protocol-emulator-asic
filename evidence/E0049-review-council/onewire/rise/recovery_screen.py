# SPDX-License-Identifier: Apache-2.0
"""Test 76 us slots on the same two-threshold public-pin fixture."""
import argparse
import itertools
import json
from pathlib import Path
import sys
from rise_screen import ROOT, ORIGINAL, candidate, check, compile_sim, make_plan, run_case, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    out = parser.parse_args().out.resolve()
    check(out.is_relative_to(ROOT / "build"), "fresh build directory required")
    out.mkdir(parents=True, exist_ok=False)
    verify(ROOT)
    compile_sim(out)
    src = candidate((ORIGINAL / "power_query.asm").read_text())
    for before, after in (("SHORT_RECOVERY 3398", "SHORT_RECOVERY 3698"),
                          ("LONG_RECOVERY 398", "LONG_RECOVERY 698")):
        check(src.count(before) == 1, "source edit")
        src = src.replace(before, after)
    info = make_plan(src, out / "wider.plan")
    reference = json.loads((ORIGINAL / "result.json").read_bytes())["cases"]["present-15-60-0"]["observed"]
    falls = [edge + 300 * max(0, index-1) for index, edge in enumerate(reference["falls"])]
    result = {"schema": "council-sensed-edge-wider-v1", "image": info, "in_envelope": [], "stress": []}
    check(info["words"] == 85 and info["load_steps"] == 712, "unexpected program size")
    for inputs in itertools.product((100, 1000), (0, 1), (15, 60), (60, 240), (15, 60)):
        result["in_envelope"].append(run_case(out, "wider", info, *inputs, falls, 114303))
    for delay, sample in ((15, 15), (60, 60)):
        result["stress"].append(run_case(out, "wider", info, 2200, 1, delay, 60, sample, falls, 114303))
    result["accepted"] = sum(r["judgment"] == "accepted" for r in result["in_envelope"])
    result["stress_rejections"] = sum(r["judgment"] != "accepted" for r in result["stress"])
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(f"wider slots: {result['accepted']}/32 accepted; {result['stress_rejections']}/2 stress rejections")
    return int(result["accepted"] != 32 or not result["stress_rejections"])


if __name__ == "__main__":
    sys.exit(main())
