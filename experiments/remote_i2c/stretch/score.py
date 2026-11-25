# SPDX-License-Identifier: Apache-2.0
"""Reconstruct native SDA/SCL and the FPGA's two drive commands from Board 4's raw capture."""
import argparse
from bisect import bisect_left
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import IMAGES, need, wire_result
from experiments.remote_i2c.receiver.score import edges, expand

SDA, SCL, SDA_OE, HALT, SCL_OE = 1, 2, 4, 8, 128
MASK = SDA | SCL | SDA_OE | HALT | SCL_OE
TICK_NS = 160
DEADLINE_NS = 4_000_000
MATRIX = {"core": [(0,0),(24,0),(24,1000),(0,1000),(0,-1),(24,-1)],
          "boundary": [(24,3850),(0,3850),(0,4150),(24,4150),(24,0),(0,0)]}


def public_bus(changes):
    bus = []
    for t, pins in changes:
        value = (2*bool(pins & SDA) + 4*bool(pins & SCL) + 16*bool(pins & SDA_OE) + 32*bool(pins & HALT))
        if not bus or value != bus[-1][1]:
            bus.append([t, value])
    return bus


def address_prefix(bus, halt):
    """Decode both address phases before a stalled read. STOP cannot occur while SCL is held low."""
    segments = []
    for (_, prev), (t, val) in zip(bus, bus[1:]):
        if t > halt:
            break
        if prev & val & 4 and (prev ^ val) & 2:
            need(not val & 2, "unexpected STOP before timeout")
            segments.append([])
        elif not prev & 4 and val & 4 and segments:
            need(not (prev ^ val) & 2, "SDA transition in SCL rise sample")
            segments[-1].append(int(bool(val & 2)))
    def bits(byte):
        return [(byte >> n) & 1 for n in reversed(range(8))]
    need(len(segments) == 2 and segments[0] == bits(0x5c)+[0]+bits(0x96)+[0,1], "decoded write and repeated START")
    read = segments[1]
    # The native peripheral may stretch on the read-address ACK or before its first data bit.
    need(read in (bits(0x5d), bits(0x5d)+[0]), "read address before the stretched clock")
    return len(read)


def measure(changes, meta):
    guard, delay = meta["guard"], meta["delay_us"]
    need(guard in IMAGES and meta["samples"] == 45000, "image and capture length")
    need(meta["idle"] == meta["recovered"] == [1,1] and meta["writes_received"] == 1
         and meta["pointer"] == 0x96 and meta["read_events"] >= 1, "peripheral received register and read request")
    if delay == -1:
        need(meta["service_us"] is None and meta["enqueued"] == 0, "withheld peripheral byte")
    else:
        need(meta["enqueued"] == 1 and meta["service_us"] >= delay, "timed peripheral FIFO write")
    pads = meta["pad_registers"]
    need([p[0] for p in pads] == [18,19,26,27] and all(p[1] == 0x5a for p in pads)
         and [p[2] & 31 for p in pads] == [3,3,5,5], "native I2C1 function and matched bias")
    values = expand(changes, meta["samples"], MASK)
    need(values[0] == (SDA|SCL), "native sampling began at idle")
    halts = edges(values, HALT)
    need(len(halts) == 1 and all((v & (SCL_OE|SDA_OE|HALT)) == HALT for v in values[halts[0]:]),
         "single stable HALT and both commands released")
    halt = halts[0]
    end_receiver = [int(bool(values[-1] & pin)) for pin in (SDA, SCL)]
    # The first job called this CPU read "at_halt". It occurs after the DMA capture.
    end_readback = meta.get("after_capture", meta.get("at_halt"))
    need(end_receiver == end_readback, "last PIO sample and end-of-capture readback")
    cmd = edges(values, SCL_OE)
    need(cmd and len(cmd)%2 == 0 and cmd[-1] < halt, "complete SCL command pairs before HALT")
    releases = cmd[1::2]
    rises = [t for t in edges(values,SCL) if values[t] & SCL]
    windows = []
    for index,t in enumerate(releases):
        end = cmd[2*index+2] if index+1 < len(releases) else halt
        pos = bisect_left(rises,t)
        rise = rises[pos] if pos < len(rises) and rises[pos] < end else None
        need(not any(v & SCL_OE for v in values[t:end]), "FPGA SCL drive during release interval")
        windows.append(None if rise is None else (rise-t)*TICK_NS)
    bus = public_bus(changes)
    measured = dict(guard=guard, requested_service_us=delay, actual_service_us=meta["service_us"],
                    status=meta["status"], rx=meta["rx"], valid=meta["valid"], halt_sample=halt,
                    release_to_receiver_high_ns=windows, scl_releases=len(releases),
                    target_request_count=meta["read_events"], samples=meta["samples"], end_receiver=end_receiver)
    if delay in (0,1000,3850):
        wire = wire_result(bus, len(values), True, 0x96, 1)
        need(wire["passed"], "native read trace: "+str(wire.get("error")))
        need([meta["status"],meta["rx"],meta["valid"]] == [0x88,1,1] and len(releases) == len(rises) == 38
             and None not in windows and max(windows) < DEADLINE_NS, "terminal byte and complete native clocks")
        if delay > 0:
            selected = [i+1 for i,ns in enumerate(windows) if ns >= 500_000]
            need(len(selected) == 1 and selected[0] in (28,29), "single read-address or first-data stretch")
            measured["stretched_release"] = selected[0]
            start = releases[selected[0]-1]
            end = start + windows[selected[0]-1] // TICK_NS
            need(all((v & (SCL | SDA_OE | SCL_OE)) == 0 for v in values[start:end]),
                 "receiver holds clock while both FPGA drive commands are released")
        measured.update(outcome="OK", longest_release_ns=max(windows), frames=wire["frames"],
                        start_to_stop_ns=(wire["boundaries"][-1][1]-wire["boundaries"][0][1])*TICK_NS)
    else:
        need(delay in (-1,4150) and meta["status"] == 0x98, "expected firmware timeout")
        need(len(releases) in (28,29) and windows.count(None) == 1 and windows[-1] is None, "single final stretched clock")
        last = releases[-1]
        need(all(not v & (SCL | SCL_OE | SDA_OE) for v in values[last:halt+1]),
             "native clock held low through HALT with both FPGA drive commands released")
        delta = (halt-last)*TICK_NS
        bounds = [delta-TICK_NS,delta+TICK_NS]
        need(bounds[1] >= DEADLINE_NS and bounds[0] <= DEADLINE_NS + 1280, "timeout outside project cleanup window")
        bits = address_prefix(bus, halt)
        need(len(releases) == 20+bits, "clock ordinal agrees with decoded address phase")
        measured.update(outcome="TIMEOUT", stretched_release=len(releases), read_address_phase_bits=bits,
                        release_to_halt_ns=delta, sample_bounds_ns=bounds,
                        interval_inside_contract=bounds[0] >= DEADLINE_NS and bounds[1] <= DEADLINE_NS+1280)
        later_rises = [t for t in rises if t > halt]
        measured["post_halt_scl_high_ns"] = (later_rises[0] - halt) * TICK_NS if later_rises else None
        if delay == -1:
            need(all(not v & SCL for v in values[last:]), "native peripheral held clock until the end of capture")
        else:
            need(len(later_rises) == 1 and end_receiver == [0, 1],
                 "late transmitter starts its first zero bit after the controller halted")
    return measured


def terminal(path):
    raw = gzip.decompress(path.read_bytes())
    need(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "complete physical terminal")
    stdout, stderr = raw[2:-2].split(b"\x04", 1)
    data = [json.loads(x[7:]) for x in stdout.splitlines() if x.startswith(b"I2CLAB ")]
    return data, stderr


def records(path):
    data, stderr = terminal(path)
    need(not stderr, "board exception")
    start, finish = data[0], data[-1]
    need(start["event"] == "start" and start["capture"] == "native-i2c1-stretch" and [start[k] for k in
         ("system_hz","core_divisor","sm_hz","sample_hz","gpio_base","in_base","mask")] ==
         [125000000,10,31250000,6250000,16,18,MASK], "physical capture configuration")
    need(finish["event"] == "finish" and finish["restored_hz"] == start["original_hz"] and finish["restored_bank"]
         and finish["host_uio_oe"] == 0, "physical cleanup")
    cold, pins, traces = {}, {}, {}
    for row in data[1:-1]:
        name = row["name"]
        if row["event"] == "cold":
            need(name not in cold, "unique load")
            cold[name] = row
            pins[name] = []
        elif row["event"] == "pins":
            need(name in cold and name not in traces and row["changes"], "sample fragment")
            pins[name].extend(row["changes"])
        else:
            need(row["event"] == "trace" and name in cold and name not in traces, "one metadata row per load")
            traces[name] = row
    need(list(cold) == list(traces) and len(traces) == 6, "six complete native trials")
    return cold, pins, traces


def check_load(row, guard):
    image = bytes.fromhex(row["image"])
    need((len(image), hashlib.sha256(image).hexdigest()) == IMAGES[guard] and
         row["registers"] == [[160, len(image)//4], [161, 0x5c], [164, 0x96]] and
         row["rows"] == (802 if guard == 0 else 902), row["name"] + " physical cold readback")


def score(path, suite):
    cold, pins, meta = records(path)
    wanted = MATRIX[suite]
    need([(r["guard"],r["delay_us"]) for r in meta.values()] == wanted, "requested physical cases")
    results = {}
    for guard, delay in wanted:
        name = f"{guard}-{delay}"
        check_load(cold[name], guard)
        results[name] = measure(pins[name], meta[name])
    return results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("suite", choices=MATRIX)
    p.add_argument("terminal", type=Path)
    opts = p.parse_args()
    print(json.dumps(score(opts.terminal, opts.suite), indent=2))
