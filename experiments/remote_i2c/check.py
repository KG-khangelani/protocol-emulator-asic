# SPDX-License-Identifier: Apache-2.0
"""Decode SCL/SDA at the RP2350 input and check each image's cold readback and outcome."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

IMAGES = {0: (384, "3cd132492f141fd056d2feae41bb2d6c52dc825d3fe4471cf17bddffffc999c2"),
          24: (432, "a4d4f8a848800f36fe04db0e2e3c6d0ee6a417b4814055cf7fb99da8c53fdc00")}
REQUESTS = ((0x96, 0x01, 0x2e), (0x55, 0xa5, 0x2e), (0x96, 0x01, 0x2f))


def need(ok, label):
    if not ok:
        raise ValueError(label)


def decode(changes, count):
    need(changes[0][0] == 0 and changes[0][1] & 6 == 6, "SDA/SCL begin idle")
    boundaries, segments, bits = [], [], []
    halts = []
    for (old_t, old), (t, new) in zip(changes, changes[1:]):
        need(old_t < t < count and old != new and new & ~0x36 == 0, "pin-change encoding")
        if (old ^ new) & 32:
            halts.append([t, (new >> 5) & 1])
        if old & new & 4 and (old ^ new) & 2:
            event = "STOP" if new & 2 else "RESTART" if boundaries else "START"
            if boundaries:
                # The last SCL rise sets up Sr/P and is outside the preceding byte.
                need(len(bits) % 9 == 1 and bits[-1][0] == int(event == "RESTART"), "Sr/STOP preparation")
                bits.pop()
                segments.append(bits)
                bits = []
            boundaries.append([event, t])
        elif not (old & 4) and new & 4 and boundaries:
            need(not ((old ^ new) & 2), "SDA changed in SCL rising sample bin")
            bits.append([(new >> 1) & 1, (new >> 4) & 1])
    need(boundaries and boundaries[-1][0] == "STOP" and not bits and changes[-1][1] & 6 == 6, "idle after STOP")
    need(len(halts) == 1 and halts[0][1] == 1 and halts[0][0] > boundaries[-1][1], "physical HALT marker")
    frames = []
    for segment in segments:
        words = []
        for i in range(0, len(segment), 9):
            group = segment[i:i + 9]
            byte = sum(bit << (7 - j) for j, (bit, _) in enumerate(group[:8]))
            words.append({"byte": byte, "ninth": group[8][0], "sda_enable": [oe for _, oe in group]})
        frames.append(words)
    return boundaries, frames, halts[0][0]


def stable_bus(changes, count, consecutive):
    """Diagnostic delayed digital filter; the strict verdict always uses the original samples."""
    raw = held = changes[0][1]
    output = [[0, raw]]
    age = {2: 0, 4: 0}
    index = 1
    for tick in range(1, count):
        if index < len(changes) and changes[index][0] == tick:
            raw = changes[index][1]
            index += 1
        for bit in age:
            if (raw ^ held) & bit:
                age[bit] += 1
                if age[bit] >= consecutive:
                    held ^= bit
                    age[bit] = 0
            else:
                age[bit] = 0
        value = (held & 6) | (raw & ~6)
        if value != output[-1][1]:
            output.append([tick, value])
    return output


def wire_result(changes, count, positive, reg, reply):
    try:
        boundaries, frames, halt = decode(changes, count)
        wanted = [[(0x5c, 0), (reg, 0)], [(0x5d, 0), (reply, 1)]] if positive else [[(0x5c, 1)]]
        actual = [[(b["byte"], b["ninth"]) for b in seg] for seg in frames]
        need(actual == wanted, "address, data or ninth bit: " + str(actual))
        need([v[0] for v in boundaries] == (["START", "RESTART", "STOP"] if positive else ["START", "STOP"]),
             "bus boundaries")
        need(all(word["sda_enable"][8] == 0 for seg in frames for word in seg), "ninth-clock ownership")
        if positive:
            need(not any(frames[1][1]["sda_enable"]), "controller release throughout target response")
        return dict(passed=True, frames=actual, boundaries=boundaries, halt_sample=halt,
                    start_to_stop_ns=100 * (boundaries[-1][1] - boundaries[0][1]))
    except ValueError as exc:
        return {"passed": False, "error": str(exc)}


def check(path):
    raw = gzip.decompress(path.read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "complete terminal response")
    stdout, errors = raw[2:-2].split(b"\x04", 1)
    need(not errors, "board exception")
    records = [json.loads(s[7:]) for s in stdout.splitlines() if s.startswith(b"I2CLAB ")]
    need(records[0]["event"] == "start" and records[0]["system_hz"] == 125000000
         and records[0]["project_divisor"] == 10 and records[0]["capture_hz"] == 10000000, "clock settings")
    need(records[-1]["event"] == "finish" and records[-1]["host_uio_oe"] == 0
         and records[-1]["restored_hz"] == records[0]["original_hz"], "controller restoration")
    expected = {f"{k}-{reg:02x}-{addr:02x}": (k, reg, reply, addr)
                for k in IMAGES for reg, reply, addr in REQUESTS}
    cold, pins, scored = {}, {}, {}
    for row in records[1:-1]:
        name = row["name"]
        cycles, reg, reply, addr = expected[name]
        event = row["event"]
        if event == "cold":
            image = bytes.fromhex(row["image"])
            need(name not in cold and (len(image), hashlib.sha256(image).hexdigest()) == IMAGES[cycles],
                 name + " image readback")
            need(row["rows"] == (802 if cycles == 0 else 902), name + " loader steps")
            need(row["registers"] == [[0xa0, len(image) // 4], [0xa1, 0x5c], [0xa4, reg]],
                 name + " length, write address or requested memory offset")
            cold[name] = len(image)
            pins[name] = []
        elif event == "pins":
            need(name in cold and name not in scored and row["changes"], name + " pin fragment")
            pins[name].extend(row["changes"])
        else:
            need(event == "trace" and name in cold and name not in scored, name + " trace inventory")
            need([row[k] for k in ("target_address", "register", "reply", "period_ns", "samples", "idle")]
                 == [addr, reg, reply, 100, 24000, [1, 1]], name + " stimulus")
            positive = addr == 0x2e
            changes = row.get("changes", pins[name])
            raw = wire_result(changes, row["samples"], positive, reg, reply)
            filtered = stable_bus(changes, row["samples"], 5)
            diagnostic = wire_result(filtered, row["samples"], positive, reg, reply)
            edges = [(tick, level & 4) for (_, old), (tick, level) in zip(changes, changes[1:]) if (level ^ old) & 4]
            brief = [(b - a) * row["period_ns"] for (a, _), (b, _) in zip(edges, edges[1:]) if b - a < 5]
            need((row["status"], row["rx"], row["valid"]) == ((0x88, reply, 1) if positive else (0x90, 0, 1)),
                 name + " outcome marker, released lines or raw register")
            scored[name] = dict(bytes_read_back=cold[name], raw_wire=raw, five_sample_diagnostic=diagnostic,
                                raw_scl_edges=len(edges), short_scl_ns=sorted(set(brief)), short_scl_runs=len(brief),
                                terminal_status=row["status"], rx=row["rx"], raw_valid=row["valid"])
    need(set(scored) == set(cold) == set(expected), "six paired physical trials")
    return scored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terminal", type=Path)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    results = check(args.terminal)
    print(json.dumps(results, indent=2))
    if not args.report_only and not all(r["raw_wire"]["passed"] for r in results.values()):
        raise SystemExit(1)
