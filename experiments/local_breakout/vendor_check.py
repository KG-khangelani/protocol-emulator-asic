# SPDX-License-Identifier: Apache-2.0
"""Read the package and connector tables independently from Lattice's pinned board schematic."""
import argparse
import hashlib
from pathlib import Path
import re

import pymupdf
from mapping import require, wiring

PDF_SHA = "2439fd0c7397f43883d13e8d92879904e669461210245906e19e329c806a022c"


def pairing(words, label_x, number_x, y_offset, y_bounds):
    # The original schematic is vector text. Read its columns and match by row.
    def column(bounds):
        return [w for w in words if bounds[0] <= w[0] <= bounds[1] and y_bounds[0] <= w[1] <= y_bounds[1]]
    numbers = [w for w in column(number_x) if w[4].isdigit()]
    result = {}
    for label in column(label_x):
        if not re.fullmatch(r"IO[BT]_[A-Z0-9_]+|ICE_CLK", label[4]):
            continue
        nearby = [n for n in numbers if abs(label[1] - n[1] - y_offset) < 1]
        require(len(nearby) == 1, "ambiguous PDF row " + str(label))
        result[label[4]] = int(nearby[0][4])
    return result


def check(path):
    require(hashlib.sha256(path.read_bytes()).hexdigest() == PDF_SHA, "Lattice guide revision 1.2")
    with pymupdf.open(path) as doc:
        package = doc[26].get_text("words")
        headers = doc[27].get_text("words")
    sg = pairing(package, (299, 307), (331, 335), 0, (248, 316))
    sg.update(pairing(package, (454, 465), (444, 448), 0, (210, 322)))
    # Fig. A.3 prints the package signal and a differently spelled off-page connector on the same wire.
    # Follow the literal connector label across both pages for this pin.
    sheet_reset = "IOT_345A_G1"
    reset_link = pairing(package, (265, 268), (331, 335), 2.3, (281, 284))
    require(reset_link.get(sheet_reset) == sg["IOT_45A_G1"] == 37, "reset off-page wire reaches pin 37")
    j2 = pairing(headers, (296, 309), (363, 370), 2.3, (288, 335))
    j2.update(pairing(headers, (414, 418), (391, 395), 2.3, (288, 335)))
    j3 = pairing(headers, (470, 480), (516, 520), 2.3, (288, 335))
    j3.update(pairing(headers, (567, 575), (543, 548), 2.3, (288, 335)))
    for row in wiring():
        header, pin = row["header"].split(".")
        net = row["net"]
        label = sheet_reset if net == "IOT_45A_G1" else net
        require(sg[net] == int(row["sg48"]) and {"J2": j2, "J3": j3}[header][label] == int(pin),
                f"{row['signal']} {net} {header}.{pin}")
    print("26 package pads and 26 connector positions match Lattice figures A.3 and A.4.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("vendor_pdf", type=Path)
    check(p.parse_args().vendor_pdf)
