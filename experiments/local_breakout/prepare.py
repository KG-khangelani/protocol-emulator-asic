# SPDX-License-Identifier: Apache-2.0
"""Construct the same public loader rows for simulated and physical bench connections."""
import argparse
import base64
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import programs
from experiments.remote_onewire.program import image as sensor_image
from experiments.remote_spi.remote import FIRMWARE, PROGRAM_SHA
from tools.assembler import assemble, load_plan
from tools.cold_load import fresh_directory


def firmware(name):
    payloads = {}
    if name == "spi":
        image = assemble(FIRMWARE.read_text())
        if image["binary_sha256"] != PROGRAM_SHA:
            raise ValueError("SPI program differs from the retained board trial")
    elif name == "onewire":
        image = sensor_image()
    else:
        image = programs()[{"release": 0, "guard": 24}[name]]
        payloads = {"TX0": 0x5c, "TX1": 0x96}
    packed = bytearray()
    for row in load_plan(image, payloads=payloads)["steps"]:
        obs = row["expected"]
        flags = (int(row["host_drives_uio"]) | (("uo_out" in obs) << 1) | (("uio_out" in obs) << 2)
                 | ((row["action"] == "flush_idle") << 3))
        packed.extend((row["rst_n"], row["ui_in"], row["uio_in"], flags,
                       obs.get("uo_out", 0), obs.get("uio_out", 0)))
    return packed, image["binary_sha256"]


def sensor_job(mode, out):
    packed, expected = firmware("onewire")
    code = ("PLAN = %r\nIMAGE_SHA = %r\nMODE = %r\n" % (base64.b64encode(packed).decode(), expected, mode)
            + (HERE / "transport.py").read_text() + "\n" + (HERE / "sensor.py").read_text())
    path = out / "pico_job.py"
    path.write_bytes(code.encode())
    print(path, hashlib.sha256(path.read_bytes()).hexdigest())
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["external", "parasite", "absent", "stuck"])
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    sensor_job(args.mode, fresh_directory(args.out))
