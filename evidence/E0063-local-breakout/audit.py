# SPDX-License-Identifier: Apache-2.0
"""Check retained hashes, rescore decoded-header logs and challenge the physical sensor scorer."""
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.local_breakout.decode import IMAGES, sha
from experiments.local_breakout.mapping import pad, require, wiring
from experiments.local_breakout.prepare import firmware, sensor_job
from experiments.local_breakout.run import observations, spi_cases
from experiments.local_breakout.score_sensor import crc8, measure, score_rows
from experiments.remote_i2c.check import wire_result
from experiments.remote_i2c.receiver.score import expand
from experiments.remote_spi.check import assess
from tools.production_sram import verify


def rejected(rows, message):
    try:
        score_rows(rows)
    except ValueError as exc:
        require(str(exc) == message, "wrong reason for acquisition rejection: "+str(exc))
        return
    raise ValueError("accepted altered acquisition: "+message)


def sensor_controls(logs, plan):
    packed, expected = plan
    result = {}
    # A constructed identity record exercises the file contract. No ROM was acquired from a device.
    prefix = bytes.fromhex("28010203040506")
    rom = (prefix+bytes([crc8(prefix)])).hex()
    image = bytes(packed[i+5] for i in range(0,len(packed),6) if packed[i+3] & 4 and packed[i+1] < 0xa0)
    for mode in ("external","parasite","absent","stuck"):
        loader, changes, terminal = observations(logs[mode], packed, expected, False)
        ident = rom if mode in ("external","parasite") else ""
        bit = int(mode == "external") if ident else None
        rows = [dict(event="identity", mode=mode, host="Raspberry Pi Pico with RP2040", rom=ident, reference_bit=bit),
                dict(event="cold", bytes=image.hex(), registers=loader["registers"]),
                dict(event="pins", changes=changes),
                dict(event="finish", samples=15000, system_hz=125000000, sample_hz=5000000, clock_divisor=10,
                     status=terminal[0], confirmed_rom=ident, confirmed_bit=bit, cleanup=True)]
        result[mode] = score_rows(rows)["status"]
        rejected(rows[:-1], "complete acquisition")
        if ident:
            bad = deepcopy(rows)
            bad[0]["rom"] = rom[:-2] + format(int(rom[-2:],16)^1,"02x")
            rejected(bad, "independent addressed power query and ROM CRC")
            bad = deepcopy(rows)
            bad[-1]["confirmed_rom"] = ""
            rejected(bad, "sensor identity and power bit after the FPGA trial")
            bad = deepcopy(rows)
            bad[0]["mode"] = "parasite" if mode == "external" else "external"
            bad[0]["reference_bit"] = bad[-1]["confirmed_bit"] = 1-bit
            rejected(bad, "command and read sample")
    return result


def audit():
    manifest = json.loads((HERE/"manifest.json").read_bytes())
    for base, group in ((HERE,"files"), (ROOT,"inputs")):
        for name, expected in manifest[group].items():
            require(sha(base/name) == expected, name)
    profile = verify(ROOT)
    require(len(profile["files_sha256"]) == 20 and profile["profile_sha256"] == manifest["profile_sha256"],
            "production physical inputs")
    for name,digest in profile["files_sha256"].items():
        raw = subprocess.check_output(["git","show","v0.1.1:"+name], cwd=ROOT)
        require(hashlib.sha256(raw).hexdigest() == digest, "published "+name)
    required_pads = sorted(pad(row) for row in wiring())
    first = json.loads((HERE/"first.json").read_bytes())
    repeat = json.loads((HERE/"repeat.json").read_bytes())
    logs = json.loads(gzip.decompress((HERE/"header-logs.json.gz").read_bytes()))
    require(set(first) == set(repeat) == set(IMAGES), "three configurations")
    for role,(image,digest) in IMAGES.items():
        record = first[role]
        require(record["decode"] == repeat[role]["decode"] and record["results"] == repeat[role]["results"]
                and record["decode"]["header_ports"] == required_pads and record["decode"]["image_sha256"] == sha(image) == digest,
                role+" repeat and image")
    uart = first["uart"]["results"]
    pins = uart["pins"]
    require(pins["two-frames"]["accepted"] == [0x96,0x69] and pins["two-frames"]["readback_bytes"] == 32
            and pins["opposed-peer"]["rejected"] == "opposed drivers on UIO1" and pins["bad-stop"]["accepted"] is None
            and pins["damaged-byte"]["rejected"] == "byte readback"
            and uart["short_clock_control"]["rejected_period_ps"] < 80000, "UART header checks")
    plans = {name:firmware(name) for name in ("spi","onewire","release","guard")}
    for name,plan in plans.items():
        role = "spi" if name == "spi" else "drain"
        bad = name+"-bad-write"
        require(observations(logs[role][bad], *plan, True)[0] == first[role]["results"][bad], bad)
    for desc in spi_cases():
        name = desc[0]
        loader, changes, terminal = observations(logs["spi"][name], *plans["spi"], False)
        status,z,lo,hi = terminal
        data = bytes(expand(changes, z+lo+hi, 127)).hex()
        score = assess(desc, dict(name=name, status=status, packed=False, count=z+lo+hi, data=data))
        require(dict(loader=loader, pad_samples=dict(released=z, driven_low=lo, driven_high=hi), **score)
                == first["spi"]["results"][name] and not score["errors"], name)
    for name in ("release","guard"):
        for positive in (True,False):
            label = name+("-read" if positive else "-nack")
            loader, changes, status = observations(logs["drain"][label], *plans[name], False)
            score = wire_result(changes, 24000, positive, 0x96, 1)
            canonical = json.loads(json.dumps(dict(loader=loader,status=status,**score)))
            require(score["passed"] and canonical == first["drain"]["results"][label], label)
    for mode in ("external","parasite","absent","stuck"):
        loader, changes, status = observations(logs["drain"][mode], *plans["onewire"], False)
        require(dict(loader=loader, **measure(mode, changes, status[0])) == first["drain"]["results"][mode], mode)
    require(sensor_controls(logs["drain"], plans["onewire"]) == {"external":136,"parasite":144,"absent":152,"stuck":152},
            "simulated acquisition controls")
    compiled = json.loads((HERE/"micropython.json").read_bytes())
    require(compiled["pio_words"] == {"project_clock":[0xe401,0xe400], "sample_pins":[0x4010]}
            and set(compiled["jobs"]) == {"external","parasite","absent","stuck"}, "four Pico compilation receipts")
    with tempfile.TemporaryDirectory(dir=ROOT/"build") as folder:
        for mode, result in compiled["jobs"].items():
            require(sha(sensor_job(mode, Path(folder))) == result["source_sha256"], "compiled source for "+mode)
    receipt = json.loads((HERE/"check-receipt.json").read_bytes())
    require(receipt["status"] == "PASS" and all(row["returncode"] == 0 for row in receipt["commands"])
            and hashlib.sha256(gzip.decompress((HERE/"check.log.gz").read_bytes())).hexdigest()
            == receipt["artifact_sha256"]["run.log"], "repository check")
    print("PASS: 3 packed images, 26 header nets, two simulations, cold readbacks, wire scoring, 20 released inputs.")


if __name__ == "__main__":
    audit()
