# SPDX-License-Identifier: Apache-2.0
"""Decode and exercise a retained FPGA configuration through the proposed physical connectors."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.fpga_uart.run import command, exercise
from experiments.local_breakout.decode import decode, IMAGES, sha
from experiments.local_breakout.mapping import require
from experiments.local_breakout.prepare import firmware
from experiments.local_breakout.score_sensor import measure
from experiments.local_breakout.transport import cold
from experiments.remote_i2c.check import wire_result
from experiments.remote_i2c.receiver.score import expand
from experiments.remote_spi.check import assess
from experiments.remote_spi.gaps import gap_schedule
from experiments.remote_spi.schedules import schedule, tick, trials
from experiments.spi_target.requester import scenario
from tools.cold_load import fresh_directory


class Journal:
    def __init__(self, path):
        self.stream = path.open("w")
        self.pins = (0, 0, 0)

    def emit(self, clock, check=0, want=0, row=0, selector=0):
        self.stream.write(" ".join(format(v, "x") for v in (*self.pins, clock, check, want, row, selector)) + "\n")

    def set(self, reset, stage, data):
        self.pins = (reset, stage, data)
        self.emit(0)

    def pulse(self):
        self.emit(1)
        self.emit(0)

    def check(self, want, row, selector):
        self.emit(0, 1, want, row, selector)
        return want  # The external Verilog comparator checks the actual sampled pins at this row.


def play(out, label, name, mode, extra=(), damage=False):
    packed, expected = firmware(name)
    journal = Journal(out / (label + ".rows"))
    try:
        cold(journal, packed, damage)
    finally:
        journal.stream.close()
    rc = command(out, label, ["vvp", "header.vvp", "+journal=" + label + ".rows", f"+mode={mode}", *extra],
                 allow_failure=damage)
    log = (out / (label + ".log")).read_text()
    if damage:
        require(rc != 0, "damaged cold load succeeded")
    return observations(log, packed, expected, damage)


def observations(log, packed, expected, damage):
    if damage:
        match = re.search(r"COLD_MISMATCH (\d+) 0*81 ([0-9a-f]+) ([0-9a-f]+)", log)
        require(match and int(match[2], 16) ^ int(match[3], 16) == 1, "wrong-byte control")
        return dict(row=int(match[1]), selector=129, expected=int(match[2], 16), observed=int(match[3], 16)), [], []
    checked = [(int(r), int(s, 16), int(v, 16)) for r, s, v in re.findall(r"^CHECK (\d+) (\w+) (\w+)", log, re.M)]
    checks = [i for i in range(len(packed)//6) if packed[6*i+3] & 6]
    require([r for r,s,v in checked] == checks, "all cold bus comparisons completed")
    image = bytes(v for r,s,v in checked if packed[r*6+3] & 4 and s < 0xa0)
    require(hashlib.sha256(image).hexdigest() == expected, "hash of actual program bytes on decoded pins")
    registers = [[s,v] for r,s,v in checked if packed[r*6+3] & 4 and s >= 0xa0]
    changes = [[int(t), int(v)] for t,v in re.findall(r"^D (\d+) (\d+)$", log, re.M)]
    marker = re.search(r"^(?:I2C|SPI|ONEWIRE) ([\d ]+)$", log, re.M)
    require(marker and changes, "complete header capture")
    return dict(bytes=len(image), sha256=expected, rows=len(packed)//6, registers=registers), changes, list(map(int,marker[1].split()))


def spi_cases():
    for item in trials("pilot"):
        if item[0] in ("normal-a4", "normal-a5", "normal-00", "pause-a4-0-0"):
            yield item
    for bit, polarity in ((0,0), (2,1)):
        yield "abort-"+str(bit), 0xa4, 500, 7, "settled", bit, polarity, 32, 640


def staged(out, role, cells):
    command(out, "compile", ["iverilog", "-g2012", "-DNO_ICE40_DEFAULT_ASSIGNMENTS", "-s", "headers_tb",
                             "-o", "header.vvp", cells, "header.v", HERE/"headers_tb.sv"])
    results = {}
    for name in (("spi",) if role == "spi" else ("release", "guard", "onewire")):
        results[name+"-bad-write"] = play(out, name+"-bad-write", name, 1 if role == "spi" else 10, damage=True)[0]
    if role == "spi":
        for item in spi_cases():
            name = item[0]
            case = (gap_schedule if item[4] == "settled" else schedule)(scenario, item)
            events = out/(name+".events")
            events.write_text("".join(f"{tick(t)} {value}\n" for t,value in case["events"]))
            count = 4*((tick(case["finish"])+67)//4)
            loader, changes, status = play(out, name, "spi", 1, [f"+events={events}", f"+samples={count}"])
            raw = bytes(expand(changes, count, 127)).hex()
            score = assess(item, dict(packed=False, data=raw, count=count, name=name, status=status[0]))
            require(not score["errors"] and sum(status[1:]) == count and status[1] > 0, name+" "+str(score))
            results[name] = dict(loader=loader, pad_samples=dict(zip(("released","driven_low","driven_high"),status[1:])), **score)
    else:
        for name in ("release", "guard"):
            for positive in (True, False):
                label = name + ("-read" if positive else "-nack")
                loader, changes, status = play(out, label, name, 10 if positive else 11)
                score = wire_result(changes, 24000, positive, 0x96, 1)
                require(score["passed"] and status == ([136,1,1] if positive else [144,0,1]), label+" "+str(score))
                results[label] = dict(loader=loader, status=status, **score)
        for k,mode in enumerate(("external", "parasite", "absent", "stuck")):
            loader, changes, status = play(out, mode, "onewire", 20+k)
            results[mode] = dict(loader=loader, **measure(mode, changes, status[0]))
    return results


def run(out, role):
    start = datetime.now(timezone.utc).isoformat()
    decode(out, role)
    cells = Path(subprocess.check_output(["yosys-config", "--datdir"], text=True).strip())/"ice40/cells_sim.v"
    if role == "uart":
        (out/"decoded.v").write_text((out/"header.v").read_text() + "\n" + (HERE/"host_pins.v").read_text())
        results = {"selected_mhz": 12.5}
        exercise(out, cells, results)
    else:
        results = staged(out, role, cells)
    record = dict(role=role, evidence="decoded FPGA header simulation", started_utc=start,
                  ended_utc=datetime.now(timezone.utc).isoformat(), cells_sha256=sha(cells),
                  decode=json.loads((out/"decode.json").read_text()), results=results)
    (out/"result.json").write_text(json.dumps(record, indent=2)+"\n")
    print(role, "PASS", list(results))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("role", choices=IMAGES)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    run(fresh_directory(args.out), args.role)
