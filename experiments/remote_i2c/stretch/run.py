# SPDX-License-Identifier: Apache-2.0
"""Capture a native I2C1 peripheral stretching SCL on the existing board-4 receiver fixture."""
import argparse
import base64
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest
from experiments.local_breakout.prepare import firmware
from experiments.remote_i2c.receiver.run import acquire, loader_source
from experiments.remote_i2c.remote import IMAGE_SHA
from experiments.remote_uart.run import clock, require
from tools.cold_load import fresh_directory
from tools.production_sram import verify

SUITES = {
    "core": [(0, 0), (24, 0), (24, 1000), (0, 1000), (0, -1), (24, -1)],
    "boundary": [(24, 3850), (0, 3850), (0, 4150), (24, 4150), (24, 0), (0, 0)],
}


def payload(suite):
    plans = {k: base64.b64encode(firmware(name)[0]).decode() for k, name in ((0, "release"), (24, "guard"))}
    loader = loader_source((ROOT/"experiments/remote_i2c/on_board.py").read_text(encoding="utf-8"))
    return (f"PLANS={plans!r}\nTRIALS={SUITES[suite]!r}\n" + loader + "\n"
            + (HERE/"on_board.py").read_text(encoding="utf-8")).encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=SUITES)
    parser.add_argument("out", type=Path)
    parser.add_argument("--wheel", type=Path, required=True)
    args = parser.parse_args()
    out = fresh_directory(args.out)
    require(digest((ROOT/"evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) == IMAGE_SHA, "FPGA image")
    code = payload(args.suite)
    (out/"job.py.gz").write_bytes(gzip.compress(code, mtime=0))
    receipt = dict(board="fpga-4", started_utc=clock(), suite=args.suite, status="INCOMPLETE", image_sha256=IMAGE_SHA,
                   profile_sha256=verify(ROOT)["profile_sha256"], code_sha256=digest(code))
    try:
        acquire(args.wheel, out, receipt, code)
        receipt["status"] = "CAPTURED"
    except Exception as err:
        receipt["error"] = str(err)
        raise
    finally:
        receipt["ended_utc"] = clock()
        (out/"result.json").write_text(json.dumps(receipt, indent=2)+"\n")


if __name__ == "__main__":
    main()
