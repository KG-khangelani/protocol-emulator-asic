# SPDX-License-Identifier: Apache-2.0
"""Decode a stock Pico's simultaneous DQ, FPGA drive command and HALT samples."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c.check import need
from experiments.remote_i2c.receiver.score import expand, edges
from experiments.remote_onewire.peer.score import command_bytes, wire_samples
from experiments.remote_onewire.score import PROGRAM

DQ, DRIVE, HALT = 1 << 11, 1 << 1, 1 << 14


def measure(mode, changes, status):
    samples = expand(changes, 15000, DQ | DRIVE | HALT)
    cmd = edges(samples, DRIVE)
    halt = edges(samples, HALT)
    need(len(halt) == 1 and samples[-1] & HALT and not samples[-1] & DRIVE, "terminal release")
    need(not samples[0] & (HALT | DRIVE), "idle command markers")
    result = dict(status=status, halt_sample=halt[0], command_pulls=len(cmd)//2)
    if mode == "stuck":
        need(status == 0x98 and not cmd and all(not v & DQ for v in samples), "stuck before reset")
    elif mode == "absent":
        dq = edges(samples, DQ)
        need(status == 0x98 and len(cmd) == len(dq) == 2 and abs(dq[0]-cmd[0]) <= 2
             and -1 <= dq[1]-cmd[1] < 75 and samples[-1] & DQ,
             "no presence after reset")
        need(abs((cmd[1]-cmd[0])*200 - 500000) <= 200, "reset command duration")
    else:
        # wire_samples expects a low-order DQ bit. The three signals here come from separate pins.
        starts, wire = wire_samples([int(bool(v & DQ)) for v in samples])
        decoded = command_bytes([int(bool(samples[t+120] & DQ)) for t in starts[:16]])
        bit = int(bool(samples[starts[-1]+75] & DQ))
        need(decoded == [0xcc, 0xb4] and bit == int(mode == "external"), "command and read sample")
        need(len(cmd) == 36 and all(abs(a-b) <= 2 for a, b in zip(starts, cmd[2::2])), "slot ownership")
        widths = [(b-a)*200 for a, b in zip(cmd[::2], cmd[1::2])]
        wanted = [500000] + [2000 if byte & (1 << i) else 62000 for byte in decoded for i in range(8)] + [2000]
        need(all(abs(a-b) <= 200 for a,b in zip(widths,wanted)), "commanded reset and slot widths")
        need(not samples[starts[-1]+75] & DRIVE and (halt[0]-starts[-1])*200 >= 60000, "read release and length")
        need(all(v & DQ for v in samples[halt[0]:]) and status == (0x88 if bit else 0x90), "idle and result")
        result.update(wire, slots=len(starts), command=decoded, bit=bit)
    return result


def crc8(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0x8c if crc & 1 else 0)
    return crc


def score_file(path):
    rows = [json.loads(line[7:]) for line in path.read_text(encoding="utf-8-sig").splitlines()
            if line.startswith("PICO1W ")]
    return score_rows(rows)


def score_rows(rows):
    need(len(rows) >= 4 and [r["event"] for r in rows[:2]] == ["identity", "cold"]
         and rows[-1]["event"] == "finish" and all(r["event"] == "pins" for r in rows[2:-1]), "complete acquisition")
    identity, cold, end = rows[0], rows[1], rows[-1]
    mode = identity["mode"]
    need(mode in ("absent", "stuck", "external", "parasite") and identity["host"] == "Raspberry Pi Pico with RP2040",
         "fixture and mode")
    rom = bytes.fromhex(identity["rom"])
    if mode in ("external", "parasite"):
        need(len(rom) == 8 and rom[0] == 0x28 and crc8(rom) == 0 and identity["reference_bit"] == int(mode == "external"),
             "independent addressed power query and ROM CRC")
    else:
        need(not rom and identity["reference_bit"] is None, "empty control fixture")
    need(hashlib.sha256(bytes.fromhex(cold["bytes"])).hexdigest() == PROGRAM and len(bytes.fromhex(cold["bytes"])) == 340
         and cold["registers"] == [[160, 85], [161, 0], [164, 0]], "firmware readback")
    need([end[k] for k in ("samples", "system_hz", "sample_hz", "clock_divisor", "cleanup")] ==
         [15000, 125000000, 5000000, 10, True], "capture settings and cleanup")
    need(end["confirmed_rom"] == identity["rom"] and end["confirmed_bit"] == identity["reference_bit"],
         "sensor identity and power bit after the FPGA trial")
    changes = [v for row in rows[2:-1] for v in row["changes"]]
    return dict(mode=mode, rom=identity["rom"], reference_bit=identity["reference_bit"],
                **measure(mode, changes, end["status"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("terminal", type=Path)
    print(json.dumps(score_file(parser.parse_args().terminal), indent=2))
