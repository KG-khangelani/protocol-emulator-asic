# SPDX-License-Identifier: Apache-2.0
"""Exercise the archived SPI fixture under five receiver bias settings on board 4."""
import argparse
import ast
import base64
import gzip
from http.cookiejar import CookieJar
import json
from pathlib import Path
import struct
import sys
from urllib.request import HTTPCookieProcessor, Request, build_opener

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from experiments.local_breakout.prepare import firmware
from experiments.remote_spi import remote
from experiments.remote_spi.check import need
from experiments.remote_spi.gaps import gap_schedule
from experiments.remote_spi.held import held_schedule
from experiments.remote_spi.schedules import schedule, tick
from experiments.spi_target.requester import scenario
from tools.cold_load import fresh_directory
from tools.production_sram import verify

BIAS = ((0, 0), (0, -1), (0, 1), (-1, -1), (1, 1))  # GPIO20, GPIO28


def schedules():
    result = {}
    for op in (0xa4, 0xa5):
        for mode in ("held", "pause", 400, 424, 480):
            key = f"{op:02x}-{mode}"
            if mode == "held":
                desc = (key, op, 250, 7, "held", 0, 1, 32)
                case = held_schedule(scenario, desc)
            elif mode == "pause":
                desc = (key, op, 250, 7, "pause", 0, 1)
                case = schedule(scenario, desc)
            else:
                desc = (key, op, 250, 7, "gaps", 0, 1, 32, mode)
                case = gap_schedule(scenario, desc)
            result[key] = desc, case
    return result


def source_parts(source, helpers):
    lines = source.splitlines(keepends=True)
    pieces = []
    found = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in helpers:
            first = min([node.lineno, *(d.lineno for d in node.decorator_list)])
            found.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            first = node.lineno
        else:
            continue
        pieces.extend(lines[first-1:node.end_lineno])
    need(found == helpers, "board helper inventory")
    return "".join(pieces)


def payload(order):
    plan, image_sha = firmware("spi")
    need(image_sha == remote.PROGRAM_SHA, "watchdog image")
    stimulus = {}
    for name, (_, case) in schedules().items():
        if order == "clock-control" and not name.endswith("-held"):
            continue
        finish = tick(case["finish"])
        words = bytearray()
        events = [(tick(t), value) for t, value in case["events"]]
        for (t, value), (end, _) in zip(events, events[1:] + [(finish + 128, 0)]):
            need(end-t >= 4, "PIO duration")
            words.extend(struct.pack("<I", ((end-t-4) << 3) | value))
        stimulus[name] = (base64.b64encode(words).decode(), 4*((finish+67)//4))
    old = (HERE.parent / "on_board.py").read_text(encoding="utf8")
    helpers = {"report", "core_clock", "requester", "pulse", "load_program"}
    names, bias = list(stimulus), list(BIAS)
    if order == "reverse":
        names.reverse()
        bias.reverse()
    header = (f"DATA={base64.b64encode(plan).decode()!r}\nCASES={stimulus!r}\n"
              f"NAMES={names!r}\nBIAS={bias!r}\nORDER={order!r}\n")
    body = (HERE / "on_board.py").read_text(encoding="utf8")
    if order == "clock-control":
        body = source_parts(body, {"branch_sampler", "physical_input"}) + "\n" + (HERE / "clock_board.py").read_text(encoding="utf8")
    return (header + source_parts(old, helpers) + "\n" + body).encode()


def acquire(wheel, out, code, rec):
    need(remote.sha(wheel.read_bytes()) == remote.WHEEL_SHA, "terminal dependency")
    sys.path.insert(0, str(wheel.resolve()))
    from websockets.sync.client import connect
    board = "fpga-4"
    page = f"{remote.SITE}/board/{board}/"
    api = f"{remote.SITE}/api/board/{board}/designs"
    jar = CookieJar()
    http = build_opener(HTTPCookieProcessor(jar))
    with http.open(page, timeout=20) as response:
        need(b"Upload your own bitstream" in response.read(), "visitor access")
    headers = {"Origin": remote.SITE, "Referer": page, "Content-Type": "application/json",
               "X-CSRFToken": next(c.value for c in jar if c.name == "csrftoken")}

    def request(url, data=None):
        with http.open(Request(url, data=data, headers=headers), timeout=90) as response:
            return json.load(response)

    status = request(page + "status.json")
    gallery = request(api)
    selected = gallery["enabled"]
    need(status["reachable"] and status["board"]["present"] and status["kind"] == "fpga" and
         status["clients"] == 0 and selected in (None, "idle_display", "tt_um_factory_test"),
         "board unavailable or in use")
    need(any(d["source"] == "upload" and d["name"] == remote.NAME for d in gallery["designs"]),
         "archived SPI configuration is unavailable")
    target = selected if selected in {d["name"] for d in gallery["designs"]} else "tt_um_factory_test"
    rec.update(previous=selected, restore_target=target, clients_before=0,
               board_identity_sha256=remote.sha(status["board"]["usb_serial"].encode()))
    need(request(page + "status.json")["clients"] == 0, "board occupied before selection")
    try:
        rec["enable"] = request(api + "/" + remote.NAME + "/enable", b"{}")
        need(request(api)["enabled"] == remote.NAME, "SPI configuration selected")
        rec["traces"] = remote.terminal(connect, board, code, out)
    finally:
        if request(api)["enabled"] == remote.NAME and request(page + "status.json")["clients"] == 0:
            rec["restore"] = request(api + "/" + target + "/enable", b"{}")
        rec["after"] = request(api)["enabled"]
    expected = 8 if rec["order"] == "clock-control" else 50
    need(rec["traces"] == expected and rec["after"] in (target, "idle_display"), "trial count and restoration")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("order", choices=("forward", "reverse", "clock-control"))
    p.add_argument("out", type=Path)
    p.add_argument("--wheel", required=True, type=Path)
    args = p.parse_args()
    out = fresh_directory(args.out)
    need(remote.sha((ROOT / "evidence/E0057-remote-spi/fabricfox-spi.bin").read_bytes()) == remote.IMAGE_SHA,
         "retained FPGA configuration")
    code = payload(args.order)
    rec = dict(board="fpga-4", order=args.order, started_utc=remote.clock(), status="INCOMPLETE",
               image_sha256=remote.IMAGE_SHA, program_sha256=remote.PROGRAM_SHA,
               profile_sha256=verify(ROOT)["profile_sha256"], job_sha256=remote.sha(code))
    (out / "job.py.gz").write_bytes(gzip.compress(code, mtime=0))
    try:
        acquire(args.wheel, out, code, rec)
        rec["status"] = "CAPTURED"
    except Exception as exc:
        rec["error"] = str(exc)
        raise
    finally:
        rec["ended_utc"] = remote.clock()
        (out / "result.json").write_bytes((json.dumps(rec, indent=2)+"\n").encode())


if __name__ == "__main__":
    main()
