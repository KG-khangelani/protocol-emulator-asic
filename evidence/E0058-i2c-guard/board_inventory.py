# SPDX-License-Identifier: Apache-2.0
"""Read the two public FPGA inventories and optionally query an idle board's existing MicroPython."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest
from experiments.remote_uart.run import SITE, WHEEL_SHA, receive_until


def get(url):
    with urlopen(url, timeout=15) as response:
        return json.load(response)


def inventory(board):
    status = get(f"{SITE}/board/{board}/status.json")
    gallery = get(f"{SITE}/api/board/{board}/designs")
    return dict(board=board, observed_utc=datetime.now(timezone.utc).isoformat(),
                reachable=status["reachable"], present=status["board"]["present"], kind=status["kind"],
                clients=status["clients"], selected=gallery["enabled"],
                identity_sha256=digest(status["board"]["usb_serial"].encode()),
                designs=[d["name"] for d in gallery["designs"]])


def runtime(board, wheel):
    """Use raw REPL to inspect class availability. No constructors, pin writes, resets or uploads."""
    if digest(wheel.read_bytes()) != WHEEL_SHA:
        raise ValueError("unexpected WebSocket library")
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect
    check = inventory(board)
    if not (check["reachable"] and check["present"] and check["kind"] == "fpga" and check["clients"] == 0
            and check["selected"] in (None, "idle_display", "tt_um_factory_test")):
        return {"before": check, "status": "occupied or unavailable"}
    code = (b"import sys,machine,rp2,json\n"
            b"print(json.dumps(dict(runtime=sys.version,machine=sys.implementation._machine,"
            b"i2c_target=hasattr(machine,'I2CTarget'),dma=hasattr(rp2,'DMA'))))\n")
    with connect(f"{SITE.replace('https:', 'wss:')}/ws/board/{board}/serial", origin=SITE,
                 open_timeout=15, close_timeout=3) as ws:
        ws.send(b"\r")
        receive_until(ws, b">>> ", 12)
        ws.send(b"\x01")
        try:
            receive_until(ws, b"CTRL-B to exit\r\n>", 8)
            ws.send(code)
            ws.send(b"\x04")
            reply = receive_until(ws, b"\x04>", 12)
        finally:
            ws.send(b"\x02")
    if not reply.startswith(b"OK"):
        raise RuntimeError("raw REPL rejected inventory query")
    stdout, stderr = reply[2:-2].split(b"\x04", 1)
    if stderr:
        raise RuntimeError(stderr.decode(errors="replace"))
    return {"before": check, "query": code.decode(), "observation": json.loads(stdout),
            "after": inventory(board)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-board", choices=("fpga-1", "fpga-4"))
    parser.add_argument("--wheel", type=Path)
    args = parser.parse_args()
    if args.runtime_board and not args.wheel:
        parser.error("--runtime-board needs --wheel")
    report = {"inventory": [inventory(b) for b in ("fpga-1", "fpga-4")]}
    if args.runtime_board:
        report["runtime"] = runtime(args.runtime_board, args.wheel)
    print(json.dumps(report, indent=2))
