# SPDX-License-Identifier: Apache-2.0
"""Exercise the portable sensor reference on a real RP2350B using a scripted open-drain peer."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiments.local_breakout.score_sensor import crc8
from experiments.remote_i2c import remote
from experiments.remote_i2c.receiver.run import acquire
from experiments.remote_uart.run import clock
from tools.cold_load import fresh_directory
from tools.production_sram import sha, verify

CASES = ("empty", "ext", "par", "bad-crc", "par", "ext")


def bits(data):
    return [(byte >> i) & 1 for byte in data for i in range(8)]


def script(name):
    """One action per slot. A separate physical sampler checks the bits written by the master."""
    high = name != "par"
    ident = bytes.fromhex("28123456789abc" if high else "286543210fedcb")
    rom = ident + bytes([crc8(ident)])
    scratch = bytes.fromhex("50054b467fff0c10")
    scratch += bytes([crc8(scratch) ^ int(name == "bad-crc")])
    actions, levels = [], []

    def reset():
        actions.append(2)  # Answer the master's reset with presence.

    def transmit(data):
        wire = bits(data)
        actions.extend([0] * len(wire))  # Listen to the master.
        levels.extend(wire)

    def reply(bit):
        actions.append(1 - bit)  # Sink a zero and release a one.
        levels.append(bit)

    def identify():
        reset()
        transmit([0xf0])
        for b in bits(rom):
            reply(b)
            reply(1 - b)
            actions.append(0)
            levels.append(b)  # Search direction chosen by the real master.
        reset()
        transmit(bytes([0x55]) + rom + bytes([0xbe]))
        for b in bits(scratch):
            reply(b)
        if name != "bad-crc":
            reset()
            transmit(bytes([0x55]) + rom + bytes([0xb4]))
            reply(int(high))

    identify()
    if name != "bad-crc":
        reset()
        transmit([0xcc, 0xb4])
        reply(int(high))
        identify()
    return dict(rom=rom.hex(), scratchpad=scratch.hex(), actions=bytes(actions), levels=bytes(levels))


def payload(order):
    cases = CASES if order == "forward" else CASES[::-1]
    vectors = {}
    for name in ("ext", "par", "bad-crc"):
        design = script(name)
        vectors[name] = base64.b64encode(design["actions"]).decode(), len(design["levels"])
    prefix = f"__name__='sensor_reference'\nCASES={cases!r}\nVECTORS={vectors!r}\n"
    return (prefix + (HERE / "pico.py").read_text(encoding="utf8") + "\n"
            + (HERE / "scripted_peer.py").read_text(encoding="utf8")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("order", choices=("forward", "reverse"))
    parser.add_argument("out", type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    args = parser.parse_args()
    out = fresh_directory(args.out)
    if sha((ROOT / "evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) != remote.IMAGE_SHA:
        raise ValueError("existing FPGA configuration")
    code = payload(args.order)
    receipt = dict(board="fpga-4", order=args.order, started_utc=clock(), status="INCOMPLETE",
                   image_sha256=remote.IMAGE_SHA, code_sha256=sha(code), profile_sha256=verify(ROOT)["profile_sha256"])
    (out / "job.py.gz").write_bytes(gzip.compress(code, mtime=0))
    try:
        acquire(args.wheel, out, receipt, code)
        receipt["status"] = "CAPTURED"
    except Exception as exc:
        receipt["error"] = str(exc)
        raise
    finally:
        receipt["ended_utc"] = clock()
        (out / "result.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
