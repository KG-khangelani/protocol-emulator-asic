"""Summarize the G4-pinned IHP pad Liberty tables named by the 0p4 precedent.

Reads three public source blobs at immutable URLs. The program writes only
JSON to stdout. The optional directory permits an offline run from exact blobs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request


PDK = "89d42ee6d2fd9b50b86a1aada6fee6673c3e6008"
BASE = f"https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/{PDK}/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/lib/"
FILES = {
    "sg13cmos5l_io_fast_1p32V_3p6V_m40C.lib": "55241e71c2278fb230ed6de3ca704907e6e8131a",
    "sg13cmos5l_io_typ_1p2V_3p3V_25C.lib": "0401964ebbe3454fd0edc882fa4ef7abaedfc371",
    "sg13cmos5l_io_slow_1p08V_3p0V_125C.lib": "9650fe2c9ef4c705d42138cec0f11ca8d1947663",
}


def nums(line):
    return [float(t.strip()) for t in line.split(",")]


def table(arc, name):
    chunk = arc.split(f"{name} (", 1)[1].split("}", 1)[0]
    x = nums(re.search(r'index_1\s*\("([^"]+)"\)', chunk)[1])
    y = nums(re.search(r'index_2\s*\("([^"]+)"\)', chunk)[1])
    vals = [nums(r) for r in re.findall(r'"([^"]+)"', chunk.split("values (", 1)[1])]
    assert len(vals) == len(x) and all(len(row) == len(y) for row in vals)
    return x, y, [v for row in vals for v in row]


def summarize(name, expected_blob, directory):
    if directory:
        raw = (directory / name).read_bytes()
    else:
        with urllib.request.urlopen(BASE + name, timeout=30) as r:
            raw = r.read()
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    assert git_blob == expected_blob, name
    lib = raw.decode("utf-8")
    for clause in ('time_unit : "1ns";', "capacitive_load_unit (1,pf);", "output_threshold_pct_fall : 50;",
                   "slew_lower_threshold_pct_fall : 10;", "slew_upper_threshold_pct_fall : 90;"):
        assert clause in lib, (name, clause)
    cell = lib.split("cell (sg13cmos5l_IOPadInOut30mA)", 1)[1].split("\n  cell (", 1)[0]
    pad = cell.split("\n    pin (pad)", 1)[1].split("\n    pin (", 1)[0]
    cap = float(re.search(r"max_capacitance\s*:\s*([^;]+);", pad)[1])
    arc = next(a for a in pad.split("timing ()") if 'related_pin : "c2p_en";' in a
               and "timing_type : three_state_enable;" in a)
    x, y, delays = table(arc, "cell_fall")
    x2, y2, slews = table(arc, "fall_transition")
    assert x == x2 and y == y2
    # If each fully monotonic output drops from >=90% to <=10%, either part
    # between 50% and 70%/30% is no longer than its full 90%-10% fall.
    early = min(d-f for d, f in zip(delays, slews))
    late = max(d+f for d, f in zip(delays, slews))
    def span(a):
        return [min(a), max(a)]
    return {"file": name, "git_blob": git_blob, "file_sha256": hashlib.sha256(raw).hexdigest(),
            "pad_max_capacitance_pf": cap, "input_slew_grid_ns": x, "output_load_grid_pf": y,
            "tabulated_points": len(delays), "oe_to_fall50_ns": span(delays),
            "fall90_to10_ns": span(slews),
            "algebra_only": {"earliest70_lower_ns": round(early, 6), "latest30_upper_ns": round(late, 6),
                             "falling_pair_order_lower_if_pad_enables_20ns_apart_ns": round(20+early-late, 6)}}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--offline", type=Path)
    args = p.parse_args()
    results = [summarize(n, v, args.offline) for n, v in FILES.items()]
    print(json.dumps({"source": "IHP Open PDK", "commit": PDK, "cell": "sg13cmos5l_IOPadInOut30mA",
                      "condition": "c2p stays low, c2p_en asserts, falling output",
                      "assumptions_for_algebra": "Both pins at one common tabulated corner, each at a grid point, monotone full swing, 20 ns between pad enable reference crossings, literal table interpretation; no route, package or board measurement.",
                      "tables": results}, indent=2))
