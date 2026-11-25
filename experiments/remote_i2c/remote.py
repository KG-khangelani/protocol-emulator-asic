# SPDX-License-Identifier: Apache-2.0
"""Run the paired firmware against the RP2350 I2C1 target on an idle FabricFox."""
import argparse
import base64
import gzip
from http.cookiejar import CookieJar
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, Request
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.i2c.guard_cases import digest, programs
from experiments.remote_uart.run import SITE, WHEEL_SHA, clock, receive_until, require
from tools.assembler import load_plan
from tools.cold_load import fresh_directory
from tools.production_sram import verify

IMAGE_SHA = "7ee587d50556b33599c23a2a893176534fafee1863d858c16d586d97c9be4bf4"
NAME = "tt_um_khangelani_i2c_" + IMAGE_SHA[:8]
MATRIX = ((0x96, 0x01, 0x2e), (0x55, 0xa5, 0x2e), (0x96, 0x01, 0x2f))


def board_code(linked_pulls=False):
    images = programs()
    plans, trials = {}, []
    for cycles in (0, 24):
        for register, reply, address in MATRIX:
            key = f"{cycles}-{register}"
            if key not in plans:
                plan = load_plan(images[cycles], payloads={"TX0": 0x5c, "TX1": register})
                packed = bytearray()
                for row in plan["steps"]:
                    observed = row["expected"]
                    flags = (int(row["host_drives_uio"]) | (("uo_out" in observed) << 1)
                             | (("uio_out" in observed) << 2) | ((row["action"] == "flush_idle") << 3))
                    packed.extend((row["rst_n"], row["ui_in"], row["uio_in"], flags,
                                   observed.get("uo_out", 0), observed.get("uio_out", 0)))
                plans[key] = base64.b64encode(packed).decode()
            trials.append((cycles, register, reply, address, key))
    return (f"PLANS={plans!r}\nTRIALS={trials!r}\nEXTRA_PULL={linked_pulls!r}\n"
            + (HERE / "on_board.py").read_text()).encode()


def terminal(connect, board, code, out):
    address = f"{SITE.replace('https:', 'wss:')}/ws/board/{board}/serial"
    with connect(address, origin=SITE, open_timeout=15, close_timeout=3) as ws:
        ws.send(b"\r")
        receive_until(ws, b">>> ", 12)
        ws.send(b"\x01")
        raw = bytearray()
        try:
            receive_until(ws, b"CTRL-B to exit\r\n>", 8)
            for i in range(0, len(code), 128):
                ws.send(code[i:i + 128])
                time.sleep(.035)
            ws.send(b"\x04")
            deadline = time.monotonic() + 180
            while not raw.endswith(b"\x04>") and time.monotonic() < deadline:
                message = ws.recv(timeout=max(.1, deadline - time.monotonic()))
                if isinstance(message, bytes):
                    raw.extend(message)
        finally:
            (out / "terminal.bin.gz").write_bytes(gzip.compress(bytes(raw), mtime=0))
            ws.send(b"\x02")
    require(raw.startswith(b"OK") and raw.endswith(b"\x04>"), "incomplete raw REPL response")
    stdout, stderr = raw[2:-2].split(b"\x04", 1)
    if stderr:
        raise RuntimeError(stderr.decode(errors="replace"))
    rows = [json.loads(s[7:]) for s in stdout.splitlines() if s.startswith(b"I2CLAB ")]
    require(rows and rows[-1].get("event") == "finish" and rows[-1]["host_uio_oe"] == 0, "controller cleanup")
    return sum(r["event"] == "trace" for r in rows)


def run(board, image, wheel, out, receipt, linked_pulls):
    data = image.read_bytes()
    require(digest(data) == IMAGE_SHA and digest(wheel.read_bytes()) == WHEEL_SHA, "FPGA or terminal identity")
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect
    payload = board_code(linked_pulls)
    receipt.update(image_sha256=IMAGE_SHA, code_sha256=digest(payload))
    page = f"{SITE}/board/{board}/"
    api = f"{SITE}/api/board/{board}"
    cookies = CookieJar()
    http = build_opener(HTTPCookieProcessor(cookies))
    with http.open(page, timeout=20) as response:
        require(b"Upload your own bitstream" in response.read(), "visitor gallery unavailable")
    token = next(c.value for c in cookies if c.name == "csrftoken")

    def request(url, body=None, content="application/json"):
        headers = {"User-Agent": "Protocol Emulator ASIC I2C bench"}
        if body is not None:
            headers.update({"Origin": SITE, "Referer": page, "X-CSRFToken": token, "Content-Type": content})
        with http.open(Request(url, data=body, headers=headers), timeout=90) as response:
            return json.load(response)

    status = request(page + "status.json")
    gallery = request(api + "/designs")
    previous = gallery["enabled"]
    receipt.update(previous=previous, clients_before=status["clients"],
                   identity_sha256=digest(status["board"]["usb_serial"].encode()))
    require(status["reachable"] and status["board"]["present"] and status["kind"] == "fpga"
            and status["clients"] == 0, "board occupied or unavailable")
    require(previous in (None, "idle_display", "tt_um_factory_test", NAME), "another design active")
    designs = {d["name"] for d in gallery["designs"]}
    restore = previous if previous in designs and previous != NAME else "tt_um_factory_test"
    require(restore in designs, "restore selection absent")
    if NAME not in designs:
        require(sum(d["source"] == "upload" for d in gallery["designs"]) < 16, "visitor gallery full")
        boundary = "i2c" + uuid4().hex
        fields = (f'--{boundary}\r\nContent-Disposition: form-data; name="name"\r\n\r\n{NAME}\r\n'
                  f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{NAME}.bin"\r\n'
                  'Content-Type: application/octet-stream\r\n\r\n').encode()
        body = fields + data + f"\r\n--{boundary}--\r\n".encode()
        receipt["upload"] = request(api + "/bitstream", body, "multipart/form-data; boundary=" + boundary)
        require(receipt["upload"].get("name") == NAME and receipt["upload"].get("size") == len(data)
                and not receipt["upload"].get("evicted"), "unexpected gallery upload")
    try:
        require(request(page + "status.json")["clients"] == 0, "board occupied before configuration")
        receipt["enable"] = request(f"{api}/designs/{NAME}/enable", b"{}")
        require(request(api + "/designs")["enabled"] == NAME, "FPGA selection")
        receipt["traces"] = terminal(connect, board, payload, out)
    finally:
        chosen = request(api + "/designs")["enabled"]
        if chosen in (None, NAME) and request(page + "status.json")["clients"] == 0:
            try:
                receipt["restore"] = request(f"{api}/designs/{restore}/enable", b"{}")
            except HTTPError as exc:
                detail = exc.read().decode(errors="replace")
                if exc.code != 502 or "MemoryError" not in detail or restore != "tt_um_factory_test":
                    raise
                from experiments.remote_i2c.recover import restore as restore_after_memory_error
                recovery = {"manager_error": detail}
                receipt["restore_recovery"] = recovery
                restore_after_memory_error(board, wheel, recovery, soft_reset=True)
        receipt["after"] = request(api + "/designs")["enabled"]
    require(receipt["after"] in (restore, "idle_display") and receipt["traces"] == 6, "restoration or inventory")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--board", required=True, choices=("fpga-1", "fpga-4"))
    p.add_argument("--image", required=True, type=Path)
    p.add_argument("--wheel", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--linked-pulls", action="store_true")
    args = p.parse_args()
    out = fresh_directory(args.out)
    rec = dict(board=args.board, started_utc=clock(), status="INCOMPLETE", linked_pulls=args.linked_pulls,
               profile_sha256=verify(ROOT)["profile_sha256"])
    try:
        run(args.board, args.image, args.wheel, out, rec, args.linked_pulls)
        rec["status"] = "CAPTURED"
    except Exception as exc:
        rec["error"] = str(exc)
        raise
    finally:
        rec["ended_utc"] = clock()
        (out / "result.json").write_text(json.dumps(rec, indent=2) + "\n")
