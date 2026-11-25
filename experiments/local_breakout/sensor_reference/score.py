# SPDX-License-Identifier: Apache-2.0
"""Decode a Pico-only power query, or check both labelled physical sensors together."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from experiments.local_breakout.score_sensor import crc8
from experiments.remote_i2c.check import need
from experiments.remote_onewire.peer.score import command_bytes


def wire(record):
    need((record["sample_hz"], record["samples"]) == (2000000, 16384), "sensor capture settings")
    data = bytes.fromhex(record["dq_lsb_first"])
    need(len(data) * 8 == record["samples"], "complete raw sensor samples")
    samples = [(b >> i) & 1 for b in data for i in range(8)]
    need(samples[0] == samples[-1] == 1, "idle sensor endpoints")
    edges = [t for t in range(1, len(samples)) if samples[t] != samples[t-1]]
    pulses = list(zip(edges[::2], edges[1::2]))
    need(len(pulses) in (19, 20), "one reset, one presence, sixteen writes and one read")
    reset, presence = pulses[:2]
    reset_ns = 500 * (reset[1] - reset[0])
    delay_ns = 500 * (presence[0] - reset[1])
    present_ns = 500 * (presence[1] - presence[0])
    # One 500 ns sample of interval quantization. Neither the probe nor this clock is calibrated.
    need(479500 <= reset_ns <= 960500 and 14500 <= delay_ns <= 60500 and 59500 <= present_ns <= 240500,
         "reset and presence at sensor")
    slots = pulses[2:19]
    need(all((b[0]-a[0])*500 >= 59500 for a,b in zip(slots, slots[1:])), "spacing of native slots")
    decoded = command_bytes([samples[start+48] for start,_ in slots[:16]])  # sample each write at 24 us
    need(decoded == [0xcc, 0xb4], "broadcast command on sensor DQ")
    widths = [(end-start)*500 for start,end in slots[:16]]
    for i, width in enumerate(widths):
        bit = (decoded[i//8] >> (i % 8)) & 1
        need((500 <= width <= 15500 if bit else 59500 <= width <= 120500), "native write-low duration")
    start = slots[-1][0]
    if len(pulses) == 20:
        need(pulses[-1][0] - start <= 31, "second low confined to the read slot")
    need((pulses[-1][1]-start)*500 <= 120500 and start+120 < len(samples), "complete read slot")
    bit = samples[start+30]  # sensor-end DQ at 15 us
    return dict(command=decoded, slots=17, wire_power=bit, reset_ns=reset_ns, presence_delay_ns=delay_ns,
                presence_ns=present_ns, write_low_ns=widths, read_low_pulses=len(pulses)-18,
                read_slot_start_sample=start)


def measurement(row):
    for ref in (row["before"], row["after"]):
        rom = bytes.fromhex(ref["rom"])
        scratch = bytes.fromhex(ref["scratchpad"])
        need(len(rom) == 8 and rom[0] == 0x28 and crc8(rom) == 0, "family-28 ROM and CRC")
        need(len(scratch) == 9 and len(set(scratch)) > 1 and crc8(scratch) == 0, "addressed scratchpad and CRC")
        need(ref["power"] in (0, 1), "addressed power response")
    result = wire(row)
    need(row["before"]["rom"] == row["after"]["rom"], "same ROM before and after")
    need(row["before"]["power"] == row["after"]["power"] == row["power"] == result["wire_power"],
         "addressed, broadcast and observed power agree")
    return dict(rom=row["before"]["rom"], scratchpad_before=row["before"]["scratchpad"],
                scratchpad_after=row["after"]["scratchpad"], **result)


def local(path):
    lines = [json.loads(line[10:]) for line in path.read_text(encoding="utf-8-sig").splitlines()
             if line.startswith("SENSORREF ")]
    need(len(lines) == 1, "one completed local sensor acquisition")
    row = lines[0]
    need((row["fixture"], row["host"], row["master_gpio"], row["sensor_gpio"]) ==
         ("local-pico", "Raspberry Pi Pico with RP2040", 19, 18), "local Pico and declared sensor-end connection")
    return measurement(row)


def pair(external, parasite):
    need(external["rom"] != parasite["rom"], "two distinct sensor ROMs")
    need(external["wire_power"] == 1 and parasite["wire_power"] == 0, "declared external and parasite VDD wiring")
    return {"external": external, "parasite": parasite}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first", type=Path, help="single terminal transcript, or the externally powered one")
    parser.add_argument("parasite", nargs="?", type=Path, help="transcript with a different sensor's VDD grounded")
    args = parser.parse_args()
    first = local(args.first)
    print(json.dumps(first if args.parasite is None else pair(first, local(args.parasite)), indent=2))
