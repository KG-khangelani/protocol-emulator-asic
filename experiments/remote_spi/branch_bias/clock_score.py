# SPDX-License-Identifier: Apache-2.0
"""Compare raw GPIO20/28 edge counts during matched running, parked and restarted clock windows."""
import argparse
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.remote_spi.branch_bias.score import NS, check_pads, session
from experiments.remote_spi.check import need


def edges(words, bit):
    return [i for i in range(1, len(words)) if (words[i] ^ words[i-1]) & (1 << bit)]


def extract(row, fragments):
    need(check_pads(row) == (0, -1) and row["packed"] is False and row["count"] == 6400
         and row["name"] in ("a4-held", "a5-held") and row["status"] == 0xbb, "raw control settings")
    data = bytearray()
    for piece in fragments:
        need(piece["name"] == row["name"] and piece["bias"] == row["bias"] and piece["offset"] == len(data),
             "contiguous raw DMA halfwords")
        data.extend(bytes.fromhex(piece["data"]))
    need(len(data) == 2*row["count"], "all raw DMA halfwords")
    words = [x[0] for x in struct.iter_unpack("<H", data)]
    cs, drive, clock = (edges(words, bit) for bit in (7,9,11))
    need(len(cs) == len(drive) == 2 and cs[0] < drive[0] < cs[1] < drive[1], "single abort and active release")
    abort, off = cs[1], drive[1]
    bit = int(row["name"] == "a5-held")
    need(all(bool(v & (1 << 8)) == bool(v & 1) == bool(bit) and v & (1 << 9) for v in words[abort-4:abort]),
         "opposite known driven levels sampled on both inputs")
    need((words[off] & 0xa0) == 0xa0 and all((v & 0x2e0) == (words[off] & 0x2e0)
         and not (v & (1 << 9)) for v in words[off:]),
         "fixed requester and disabled FPGA gate through the control")
    intervals = list(zip(clock, clock[1:]))
    pauses = [(a,b) for a,b in intervals if b-a > 8]
    need(len(pauses) == int(row["parked"]) and clock[0] < 10 and len(words)-clock[-1] < 10
         and all(4 <= b-a <= 6 for a,b in intervals if b-a <= 8), "witnessed running or parked clock")
    pause = None
    if pauses:
        a,b = pauses[0]
        need(a > off and 995 <= b-a <= 1020 and not words[a] & (1 << 11) and words[b] & (1 << 11),
             "eight-microsecond low-clock control")
        pause = (a-abort, b-abort)
    return dict(name=row["name"], repeat=row["repeat"], parked=row["parked"], words=words,
                abort=abort, off=off, pause=pause, status=row["status"])


def compare(record, window):
    abort = record["abort"]
    a, b = (abort + offset for offset in window)
    width = b-a
    need(a-width >= record["off"] and b+width < len(record["words"]), "equal released comparison windows")
    output = {}
    words = record["words"]
    for label, left, right in (("before", a-width, a), ("during", a, b), ("after", b, b+width)):
        # Leave two 8 ns samples at either edge to avoid a boundary affecting the count.
        lo, hi = left+2, right-2
        output[label] = {"samples":hi-lo, "start_after_abort_ns":(lo-abort)*NS}
        for signal, number in (("clock",11), ("gp20",0), ("gp28",8)):
            output[label][signal+"_edges"] = sum(bool((words[t] ^ words[t-1]) & (1 << number)) for t in range(lo,hi))
            output[label][signal+"_high_samples"] = sum(bool(v & (1 << number)) for v in words[lo:hi])
    return dict(name=record["name"], repeat=record["repeat"], parked=record["parked"], status=record["status"],
                abort_to_oe_ns=(record["off"]-abort)*NS, compared_clock_low_ns=width*NS, windows=output)


def score(path):
    _, rows = session(path, ("clock-control",))
    captures, fragments = [], []
    for row in rows:
        if row["event"] == "raw":
            fragments.append(row)
        else:
            need(row["event"] == "trace", "raw clock-control record")
            captures.append(extract(row, fragments))
            fragments = []
    pins = [("a4-held",False), ("a5-held",True), ("a4-held",True), ("a5-held",False)]
    expected = [(n,p,0) for n,p in pins] + [(n,p,1) for n,p in reversed(pins)]
    need(not fragments and [(r["name"],r["parked"],r["repeat"]) for r in captures] == expected,
         "complete counterbalanced clock controls")
    windows = {(r["name"],r["repeat"]):r["pause"] for r in captures if r["parked"]}
    return [compare(r, windows[(r["name"],r["repeat"])]) for r in captures]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("terminal", type=Path)
    print(json.dumps(score(p.parse_args().terminal), indent=2))
