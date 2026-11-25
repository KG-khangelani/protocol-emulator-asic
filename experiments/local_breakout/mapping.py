# SPDX-License-Identifier: Apache-2.0
"""Check physical pin assignments and name the decoded iCE40 pads after board connectors."""
import csv
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PCF = ROOT / "experiments/fpga_uart/tt_fpga_fabricfoxv2.pcf"


def require(ok, message):
    if not ok:
        raise ValueError(message)


def wiring():
    with (HERE / "wiring.csv").open(newline="") as file:
        rows = list(csv.DictReader(file))
    gpios = [*range(23), 26, 27, 28]
    physical = [1, 2, 4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 17, 19, 20, 21, 22, 24, 25, 26, 27, 29, 31, 32, 34]
    pico = dict(zip(gpios, physical))
    pins = dict(re.findall(r"^set_io -nowarn (\S+)\s+(\d+)$", PCF.read_text(), re.M))
    expected = {"clk", "rst_n"} | {f"{bus}[{i}]" for bus in ("ui_in", "uo_out", "uio") for i in range(8)}
    require({r["signal"] for r in rows} == expected and len(rows) == 26, "26 public signals")
    for key in ("sg48", "header", "pico_gpio", "pico_header"):
        require(len({r[key] for r in rows}) == len(rows), "duplicate " + key)
    require({int(r["pico_gpio"]) for r in rows} == set(pico), "Pico GPIO inventory")
    for row in rows:
        require(pins[row["signal"]] == row["sg48"], row["signal"] + " production FPGA assignment")
        require(pico[int(row["pico_gpio"])] == int(row["pico_header"]), row["signal"] + " Pico header")
    return rows


def pad(row):
    return row["header"].lower().replace(".", "_")
