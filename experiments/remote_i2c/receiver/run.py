# SPDX-License-Identifier: Apache-2.0
"""Use the existing board-4 I²C configuration to capture GPIO19 through GPIO34 simultaneously."""
import argparse
import ast
from http.cookiejar import CookieJar
import gzip
import json
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, HTTPCookieProcessor, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiments.remote_i2c import remote
from experiments.remote_i2c.recover import restore
from experiments.remote_uart.run import SITE, WHEEL_SHA, clock, require
from experiments.i2c.guard_cases import digest
from tools.cold_load import fresh_directory
from tools.production_sram import verify


def payload(hz, extra, swap_target=False, both_sda=False):
    """Reuse the exact plans and the MicroPython clock/loader functions from the earlier capture."""
    require(hz in (8_000_000, 10_000_000), "specified sample rates")
    require(not swap_target or extra, "paired pin swap requires equal requested pull-up settings")
    original = remote.board_code(extra).decode()
    lines = original.splitlines(keepends=True)
    pieces = []
    helpers = {"emit", "project_clock", "pulse", "load_program"}
    found = set()
    for node in ast.parse(original).body:
        start = node.lineno
        if isinstance(node, ast.FunctionDef) and node.name in helpers:
            found.add(node.name)
            start = min([start, *(d.lineno for d in node.decorator_list)])
        elif not isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign)):
            continue
        pieces.extend(lines[start - 1:node.end_lineno])
    require(found == helpers, "E0059 loader function inventory")
    sda, scl = (18, 19) if swap_target else (26, 27)
    pieces.extend([f"\nSAMPLE_HZ={hz}\nTARGET_SDA={sda}\nTARGET_SCL={scl}\nBOTH_SDA={both_sda!r}\n",
                   (HERE / "on_board.py").read_text(encoding="utf-8")])
    return "".join(pieces).encode()


def acquire(wheel, out, receipt, code):
    require(digest(wheel.read_bytes()) == WHEEL_SHA, "WebSocket client identity")
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect

    board = "fpga-4"
    page = f"{SITE}/board/{board}/"
    designs = f"{SITE}/api/board/{board}/designs"
    jar = CookieJar()
    http = build_opener(HTTPCookieProcessor(jar))
    with http.open(page, timeout=20) as response:
        require(b"Upload your own bitstream" in response.read(), "public visitor board")
    headers = {"Origin": SITE, "Referer": page, "Content-Type": "application/json",
               "X-CSRFToken": next(c.value for c in jar if c.name == "csrftoken")}

    def request(url, body=None):
        with http.open(Request(url, data=body, headers=headers), timeout=90) as response:
            return json.load(response)

    status = request(page + "status.json")
    gallery = request(designs)
    names = {item["name"] for item in gallery["designs"] if item["source"] == "upload"}
    require(status["reachable"] and status["board"]["present"] and status["kind"] == "fpga"
            and status["clients"] == 0, "board unavailable or occupied")
    previous = gallery["enabled"]
    require(previous in (None, "idle_display", "tt_um_factory_test") and remote.NAME in names,
            "existing E0059 visitor configuration and idle board required")
    target = previous if previous in {d["name"] for d in gallery["designs"]} else "tt_um_factory_test"
    receipt.update(previous=previous, restore_target=target, clients_before=status["clients"],
                   identity_sha256=digest(status["board"]["usb_serial"].encode()))
    require(request(page + "status.json")["clients"] == 0, "board occupied before selection")
    try:
        receipt["enable"] = request(f"{designs}/{remote.NAME}/enable", b"{}")
        require(request(designs)["enabled"] == remote.NAME, "selected I²C configuration")
        receipt["traces"] = remote.terminal(connect, board, code, out)
    finally:
        if request(designs)["enabled"] == remote.NAME and request(page + "status.json")["clients"] == 0:
            try:
                receipt["restore"] = request(f"{designs}/{target}/enable", b"{}")
            except HTTPError as err:
                detail = err.read().decode(errors="replace")
                if err.code != 502 or "MemoryError" not in detail or target != "tt_um_factory_test":
                    raise
                recovery = {"manager_error": detail}
                receipt["restore_recovery"] = recovery
                restore(board, wheel, recovery, soft_reset=True)
        receipt["after"] = request(designs)["enabled"]
    require(receipt["traces"] == 6 and receipt["after"] in (target, "idle_display"), "capture and restoration")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--hz", type=int, choices=(8_000_000, 10_000_000), default=10_000_000)
    parser.add_argument("--linked-pulls", action="store_true")
    parser.add_argument("--swap-target", action="store_true", help="select I2C1 on GPIO18/19 during the four-pull-up trial")
    parser.add_argument("--both-sda", action="store_true", help="capture each receiver's SDA and SCL on a single PIO snapshot")
    args = parser.parse_args()
    out = fresh_directory(args.out)
    image = ROOT / "evidence/E0059-remote-i2c/fabricfox.bin"
    require(digest(image.read_bytes()) == remote.IMAGE_SHA, "E0059 configuration identity")
    code = payload(args.hz, args.linked_pulls, args.swap_target, args.both_sda)
    (out / "job.py.gz").write_bytes(gzip.compress(code, mtime=0))
    receipt = dict(board="fpga-4", started_utc=clock(), linked_pulls=args.linked_pulls, sample_hz=args.hz,
                   image_sha256=remote.IMAGE_SHA, code_sha256=digest(code), status="INCOMPLETE",
                   swap_target=args.swap_target, both_sda=args.both_sda,
                   profile_sha256=verify(ROOT)["profile_sha256"])
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
