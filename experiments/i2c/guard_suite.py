# SPDX-License-Identifier: Apache-2.0
"""Observe the selected I²C chip, an independently scheduled target, and all loader readbacks."""
import gzip
import json
import os
from pathlib import Path
import sys

import cocotb

sys.path.insert(0, os.environ["I2C_GUARD_ROOT"])
from experiments.i2c.guard_cases import BASE, PANEL, cases, digest, encoded, programs, reference
from experiments.i2c.public_bus import run_bus
from experiments.i2c.target import Target
from tools.assembler import load_plan, program_bytes
from tools.host_transport.controller import cold_load
from tools.host_transport.digital import DigitalPins
from tools.i2c_oracle import CLEANUP, assess

sys.path.insert(0, str(PANEL / "sources"))
from guard_screen import measure, witness
from retime_screen import reference_events
from experiments.i2c.guard_cases import ROOT


@cocotb.test()
async def compare_guards(dut):
    output = Path(os.environ["I2C_GUARD_OUT"])
    images = programs()
    historic = reference()
    original, _ = witness(ROOT)
    assert original["words"] == images[0]["words"]
    assert original["data"] == {"1": BASE.address << 1, "4": BASE.tx}
    peer_response = original["record"]["response"]
    assert peer_response == 690
    baseline_events = reference_events(original["trace"], assess(original["trace"], BASE))
    selected = list(cases())
    if os.environ.get("I2C_GUARD_SMOKE") == "1":
        names = {"plain-0", "plain-24", "plain-171", "24-nack-data", "24-final-1", "24-late-38", "0-data-77-55"}
        selected = [item for item in selected if item[0] in names]
    plans = {}
    failures = []
    with (output/"cases.jsonl").open("wb") as journal, (output/"traces.jsonl.gz").open("wb") as raw_file, \
            gzip.GzipFile(filename="", fileobj=raw_file, mode="wb", mtime=0) as pins_archive:
        for name, clocks, intent, stretches, historical_key in selected:
            image = images[clocks]
            payload = {"TX0": intent.address << 1, "TX1": intent.tx}
            key = clocks, intent.address, intent.tx
            if key not in plans:
                plans[key] = load_plan(image, payloads=payload)
            pins = DigitalPins(dut)
            loaded = await cold_load(pins, plans[key])
            readback = bytes(row["actual"]["uio_out"] for row in loaded if row["action"]=="read_byte_after_edge")
            assert readback == program_bytes(image) and pins.launched and pins.handoff == [0xe7,0x67,0]
            peer = Target(intent, response=peer_response, stretches=stretches)
            rows = await run_bus(dut, peer, bound_ticks=350000, extended_pc=True)
            start = next(i for i,r in enumerate(rows) if (r["oe"],r["out"],r["bus"])==(28,0,3))
            assert all((r["out"] & r["oe"] & 3)==0 for r in rows[:start+1])
            trace = [dict(r,t=r["t"]-rows[start]["t"]) for r in rows[start:]]
            verdict = assess(trace,intent)
            errors = sorted({e["kind"] for e in verdict["errors"]})
            trace_sha = digest(encoded(trace))
            expected_sha = historic[historical_key]["trace_sha256"] if historical_key else None
            if name=="plain-0":
                expected_sha = original["record"]["trace_sha256"]
            record = dict(name=name, clocks=clocks, address=intent.address, tx=intent.tx, rx=intent.rx,
                          nack=intent.nack, stretches=stretches, timeout_release=intent.timeout_release,
                          readback_sha256=digest(readback), readback_bytes=len(readback), loader_steps=len(loaded),
                          trace_sha256=trace_sha, oracle_errors=errors, expected_outcome=intent.outcome,
                          terminal_marker=(trace[-1]["out"]>>2)&7, halt_tick=verdict["halt"], releases=verdict["releases"],
                          target_decoded=peer.decoded)
            good = errors == (["data_valid_delay"] if clocks==171 else []) and (expected_sha is None or trace_sha==expected_sha)
            if name.startswith("plain-"):
                record["timing"] = measure(trace,verdict)
                record["event_times_match_release"] = reference_events(trace,verdict)==baseline_events
                good = good and record["event_times_match_release"]
            if intent.timeout_release is not None:
                released = [b["t"] for a,b in zip(trace,trace[1:]) if a["oe"]&1 and not b["oe"]&1]
                slack = verdict["halt"]-released[intent.timeout_release-1]-200000
                record["timeout_cleanup_ticks"] = slack
                good = good and 0 <= slack <= CLEANUP
                if historical_key:
                    good = good and slack == historic[historical_key]["halt_ticks_after_deadline"]
            record["expectation_matched"] = good
            journal.write(encoded(record))
            journal.flush()
            pins_archive.write(encoded([name,trace]))
            if not good:
                if not failures:
                    (output/"first-failure.json").write_bytes(encoded(dict(record=record,expected_sha256=expected_sha,
                                                                          errors=verdict["errors"][:6],trace=trace)))
                failures.append(name)
    assert not failures, f"{len(failures)} unexpected outcomes; first: {failures[:3]}"
