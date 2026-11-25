# SPDX-License-Identifier: Apache-2.0
"""Unpack a retained bitstream using the names of the Lattice breakout header pins."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.fpga_uart.run import command
from experiments.local_breakout.mapping import pad, require, wiring
from experiments.remote_i2c.remote import IMAGE_SHA as I2C_SHA
from experiments.remote_spi.remote import IMAGE_SHA as SPI_SHA
from experiments.remote_uart.run import IMAGE as UART_IMAGE, IMAGE_SHA as UART_SHA
from tools.cold_load import fresh_directory
from tools.production_sram import verify

IMAGES = {"uart": (UART_IMAGE, UART_SHA),
          "spi": (ROOT / "evidence/E0057-remote-spi/fabricfox-spi.bin", SPI_SHA),
          "drain": (ROOT / "evidence/E0059-remote-i2c/fabricfox.bin", I2C_SHA)}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def decode(out, role):
    image, expected = IMAGES[role]
    require(sha(image) == expected, "retained FPGA image")
    rows = wiring()
    pins = out / "header.pcf"
    pins.write_text("".join(f"set_io {pad(r)} {r['sg48']}\n" for r in rows))
    command(out, "unpack", ["iceunpack", image, "image.asc"])
    command(out, "repack", ["icepack", "image.asc", "roundtrip.bin"])
    require(sha(out / "roundtrip.bin") == expected, "packed image round trip")
    netlist = out / "header.v"
    with netlist.open("wb") as stream:
        command(out, "decode", ["icebox_vlog", "-S", "-c", "-d", "sg48", "-p", pins,
                                "-n", "header_image", "image.asc"], stdout=stream, env=dict(os.environ, PYTHONHASHSEED="0"))
    module_ports = netlist.read_text().split("module header_image", 1)[1].split(");", 1)[0]
    used = set(re.findall(r"\bj[23]_\d+\b", module_ports))
    names = re.findall(r"\b(?:input|output|inout)\s+(\w+)", module_ports)
    require(used == {pad(r) for r in rows} == set(names) and len(names) == 26, "all decoded package pads")
    # Connect the host model's Pico GPIOs to the reconstructed breakout headers.
    ports = ", ".join(f".{pad(r)}(gp[{r['pico_gpio']}])" for r in rows if pad(r) in used)
    (out / "header_instance.vh").write_text("header_image target (" + ports + ");\n")
    receipt = dict(role=role, image_sha256=expected, decoded_sha256=sha(netlist), header_sha256=sha(pins),
                   header_ports=sorted(used), profile_sha256=verify(ROOT)["profile_sha256"])
    (out / "decode.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(role, len(used), expected)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("role", choices=IMAGES)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    decode(fresh_directory(args.out), args.role)
