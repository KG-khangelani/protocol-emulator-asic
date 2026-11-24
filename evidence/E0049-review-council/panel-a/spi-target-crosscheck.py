"""Reduce panel C's retained SPI target case records without running its scorer."""
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

base = Path(sys.argv[1] if len(sys.argv) > 1 else "evidence/E0049-review-council/panel-c/spi-target")
records = base / "records"


def zipped(path):
    return gzip.decompress((records / path).read_bytes())


def trace(implementation):
    lines = [line.split() for line in zipped(f"{implementation}/abort.log.gz").decode().splitlines()]
    edges = [row for row in lines if row[0] == "R"]
    falls = [int(row[1]) for row in lines if row[0] == "F"]
    chip_select = next(int(row[1]) for row in lines if row[0] == "CS" and row[2] == "1")
    oe = [(int(row[1]), int(row[2], 16)) for row in lines if row[0] == "O"]
    assert [int(row[2]) for row in edges] == list(range(9))
    assert {int(b[1]) - int(a[1]) for a, b in zip(edges, edges[1:])} == {500}
    assert int("".join(row[3] for row in edges[:8]), 2) == 0xA5
    assert int(edges[-1][4], 16) & 8 and int(edges[-1][5], 16) & 8
    assert not any(t > int(edges[-1][1]) for t in falls)
    assert [mask for t, mask in oe if t <= chip_select][-1] & 8
    released = next(t for t, mask in oe if t >= chip_select and not mask & 8)
    term = next(row for row in lines if row[0] == "TERM")
    return [int(edges[-1][1]), chip_select, released, int(term[1]), int(term[2])]


def normal_reply(case):
    return (case.get("reply") == 0xA7 and case["min_miso_setup_ns"] >= 60
            and case["min_miso_hold_ns"] >= 40
            and 0 <= case["miso_release_after_last_fall_ns"] <= 160)


rtl, gate = (json.loads(zipped(f"{impl}/cases.json.gz")) for impl in ("rtl", "g4_netlist"))
counts = Counter(name.partition("-")[0] for name in rtl)
assert {key: rtl[key] for key in gate} == gate
assert {k for k in rtl if k.startswith("all-")} == {f"all-{i:02x}" for i in range(256)}
nominal_ok = {k: v["reply"] for k, v in rtl.items() if k.startswith("all-") and v["outcome"] == "OK"}
assert nominal_ok == {"all-a4": 0x3C, "all-a5": 0xA7}
assert sum(k.startswith("all-") and v["outcome"] == "BAD_OPCODE" for k, v in rtl.items()) == 254
assert trace("rtl") == trace("g4_netlist") == [4507, 4647, 6210, 6231, 3]

sweep = {int(k): row for k, row in json.loads(zipped("timeout-sweep.json.gz")).items()}
assert set(sweep) == set(range(81))
assert all(set(row["normal"]) == {"1", "7", "13", "19"} for row in sweep.values())
slow = [d for d in sorted(sweep) if all(normal_reply(case) for case in sweep[d]["normal"].values())]
fast = [d for d in sorted(sweep) if 0 <= sweep[d]["abort"].get("miso_release_ns", -1) <= 160]
assert slow == list(range(48, 81)) and fast == list(range(2, 10))
assert [sweep[d]["abort"]["last_oe_change_minus_cs_ns"] for d in (0, 1)] == [-37, -17]
assert all(sweep[d]["abort"]["miso_release_ns"] == 20*d - 37 for d in range(2, 81))
oplines = re.compile(r"^\s*(?:WAIT_PIN|SET|LOOP|SHIFT_STEP|HALT)\b", re.M)
source_counts = [len(oplines.findall(p.read_text())) for p in
                 (base / "spi_test_target.asm", records / "over-capacity-cooperative.asm")]
assert source_counts == [59, 215]
assert not json.loads((records / "trade.json").read_text())["cooperative"]["assembled"]
print(json.dumps({"rtl": len(rtl), "gate_subset": sorted(gate), "rtl_named_name_prefixes": counts,
                  "rtl_outcomes": Counter(v["outcome"] for v in rtl.values()),
                  "abort_ns_last_rise_cs_oe_term_marker": trace("rtl"),
                  "timeout_0_to_80_normal_and_abort_trials": [4*len(sweep), len(sweep)],
                  "normal_range": [slow[0], slow[-1]], "abort_range": [fast[0], fast[-1]],
                  "intersection": sorted(set(slow) & set(fast)), "source_counts": source_counts},
                 indent=2))
