# SPDX-License-Identifier: Apache-2.0
"""Free the I2C experiment's volatile data so the board manager can reload its stock bitstream."""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
import sys
from urllib.request import build_opener, HTTPCookieProcessor, Request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest
from experiments.remote_i2c.remote import NAME
from experiments.remote_uart.run import SITE, WHEEL_SHA, clock, receive_until, require


def restore(board, wheel, record, soft_reset=False):
    require(digest(wheel.read_bytes()) == WHEEL_SHA, "terminal library")
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect
    page = f"{SITE}/board/{board}/"
    api = f"{SITE}/api/board/{board}/designs"
    jar = CookieJar()
    http = build_opener(HTTPCookieProcessor(jar))
    with http.open(page, timeout=15) as response:
        response.read()
    token = next(c.value for c in jar if c.name == "csrftoken")

    def get(url):
        with http.open(url, timeout=15) as response:
            return json.load(response)

    chosen = get(api)["enabled"]
    record["before"] = chosen
    if chosen in ("tt_um_factory_test", "idle_display"):
        record["after"] = chosen
        return
    require(chosen == NAME and get(page + "status.json")["clients"] == 0, "another visitor's session")
    address = f"{SITE.replace('https:', 'wss:')}/ws/board/{board}/serial"
    with connect(address, origin=SITE, open_timeout=15, close_timeout=3) as ws:
        ws.send(b"\r")
        receive_until(ws, b">>> ", 12)
        ws.send(b"\x01")
        try:
            receive_until(ws, b"CTRL-B to exit\r\n>", 8)
            ws.send(b"import gc\nprint(gc.mem_free())\nglobals().pop('PLANS',None) is None\n"
                    b"globals().pop('TRIALS',None) is None\ngc.collect()\nprint(gc.mem_free())\n")
            ws.send(b"\x04")
            record["heap_response"] = receive_until(ws, b"\x04>", 15).decode(errors="replace")
        finally:
            ws.send(b"\x02")
        if soft_reset:
            receive_until(ws, b">>> ", 12)
            # The stock manager loads a 104090-byte image in one allocation. A
            # MicroPython soft restart coalesces the idle visitor's fragmented heap.
            ws.send(b"\x04")
            boot = receive_until(ws, b">>> ", 35)
            record["soft_restart"] = {"bytes": len(boot), "sha256": digest(boot), "returned_to_prompt": True}
    chosen = get(api)["enabled"]
    if chosen == NAME:
        require(get(page + "status.json")["clients"] == 0, "board occupied before restoration")
        headers = {"Origin": SITE, "Referer": page, "Content-Type": "application/json", "X-CSRFToken": token}
        with http.open(Request(api + "/tt_um_factory_test/enable", data=b"{}", headers=headers), timeout=90) as r:
            record["restore"] = json.load(r)
    record["after"] = get(api)["enabled"]
    require(record["after"] in ("tt_um_factory_test", "idle_display"), "board restoration")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("board", choices=("fpga-1", "fpga-4"))
    p.add_argument("wheel", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--soft-reset", action="store_true")
    args = p.parse_args()
    record = dict(board=args.board, started_utc=clock())
    with args.output.open("x") as out:
        try:
            restore(args.board, args.wheel, record, args.soft_reset)
        finally:
            record["ended_utc"] = clock()
            json.dump(record, out, indent=2)
            out.write("\n")
