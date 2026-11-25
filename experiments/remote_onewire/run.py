# SPDX-License-Identifier: Apache-2.0
"""Run the three negative 1-Wire controls twice on the previously verified board-4 image."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest
from experiments.remote_i2c.receiver.run import acquire, loader_source
from experiments.remote_i2c.remote import IMAGE_SHA
from experiments.remote_onewire.program import image
from experiments.remote_uart.run import clock, require
from tools.assembler import load_plan
from tools.cold_load import fresh_directory
from tools.production_sram import verify


def payload():
    plan = load_plan(image())
    packed = bytearray()
    for step in plan["steps"]:
        obs = step["expected"]
        flags = (int(step["host_drives_uio"]) | (("uo_out" in obs) << 1) | (("uio_out" in obs) << 2)
                 | ((step["action"] == "flush_idle") << 3))
        packed.extend((step["rst_n"], step["ui_in"], step["uio_in"], flags, obs.get("uo_out", 0), obs.get("uio_out", 0)))
    data = base64.b64encode(packed).decode()
    helpers = loader_source((ROOT / "experiments/remote_i2c/on_board.py").read_text(encoding="utf-8"))
    return (f"PLAN={data!r}\n" + helpers + (HERE / "on_board.py").read_text(encoding="utf-8")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--wheel", type=Path, required=True)
    args = parser.parse_args()
    out = fresh_directory(args.out)
    require(digest((ROOT / "evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) == IMAGE_SHA, "FPGA configuration")
    raw = payload()
    (out / "job.py.gz").write_bytes(gzip.compress(raw, mtime=0))
    receipt = dict(board="fpga-4", started_utc=clock(), status="INCOMPLETE", image_sha256=IMAGE_SHA,
                   program_sha256=image()["binary_sha256"], profile_sha256=verify(ROOT)["profile_sha256"],
                   code_sha256=digest(raw))
    try:
        acquire(args.wheel, out, receipt, raw)
        receipt["status"] = "CAPTURED"
    except Exception as err:
        receipt["error"] = str(err)
        raise
    finally:
        receipt["ended_utc"] = clock()
        (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
