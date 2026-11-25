# SPDX-License-Identifier: Apache-2.0
"""Run a 17-slot open-drain peer against the retained E0061 board firmware."""
import argparse
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest
from experiments.remote_i2c.receiver.run import acquire, loader_source
from experiments.remote_i2c.remote import IMAGE_SHA
from experiments.remote_onewire.run import payload as control_payload
from experiments.remote_onewire.score import PROGRAM
from experiments.remote_uart.run import clock, require
from tools.cold_load import fresh_directory
from tools.production_sram import verify

TRIALS = ((25, 1, True), (55, 0, True), (25, 0, True), (55, 1, True), (25, 0, False), (55, 0, False))


def payload():
    loader = loader_source(control_payload().decode())
    return (loader + f"\nTRIALS={TRIALS!r}\n" + (HERE / "on_board.py").read_text(encoding="utf-8")).encode()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--wheel", type=Path, required=True)
    args = p.parse_args()
    out = fresh_directory(args.out)
    require(digest((ROOT / "evidence/E0059-remote-i2c/fabricfox.bin").read_bytes()) == IMAGE_SHA, "FPGA configuration")
    code = payload()
    (out / "job.py.gz").write_bytes(gzip.compress(code, mtime=0))
    receipt = dict(board="fpga-4", started_utc=clock(), status="INCOMPLETE", image_sha256=IMAGE_SHA,
                   program_sha256=PROGRAM, profile_sha256=verify(ROOT)["profile_sha256"], code_sha256=digest(code))
    try:
        acquire(args.wheel, out, receipt, code)
        receipt["status"] = "CAPTURED"
    except Exception as err:
        receipt["error"] = str(err)
        raise
    finally:
        receipt["ended_utc"] = clock()
        (out / "result.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
