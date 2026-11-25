# SPDX-License-Identifier: Apache-2.0
"""Retarget the council's DS18B20 power-query program to the measured FPGA bench."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble

COUNCIL = ROOT / "evidence/E0049-review-council/onewire"


def source(variant="normal"):
    text = (COUNCIL / "power_query.asm").read_text(encoding="utf-8")
    edits = (
        ("The 20 ns time base makes 50 edges per microsecond.", "The 80 ns FPGA clock gives 12.5 edges per microsecond."),
        ("Result appears on GPIO 2:1.", "Result appears on GPIO 3:2."),
        (".const SHORT 298", ".const SHORT 23"), (".const LONG 3098", ".const LONG 773"),
        (".const SHORT_RECOVERY 3198", ".const SHORT_RECOVERY 923"),
        (".const LONG_RECOVERY 398", ".const LONG_RECOVERY 173"),
        ("cycles=24998", "cycles=6248"), ("cycles=3498", "cycles=910"), ("cycles=21497", "cycles=5335"),
        ("cycles=398", "cycles=148"), ("cycles=2798", "cycles=698"),
        ("mask=7 value=2 oe=6", "mask=13 value=4 oe=12"),
        ("mask=7 value=4 oe=6", "mask=13 value=8 oe=12"),
        ("mask=7 value=6 oe=6", "mask=13 value=12 oe=12"),
    )
    for before, after in edits:
        if text.count(before) != (2 if before == "cycles=2798" else 1):
            raise ValueError("unexpected original timing or marker: " + before)
        text = text.replace(before, after)
    if variant == "short-reset":
        text = text.replace("cycles=6248", "cycles=4998")
    elif variant == "bad-command":
        text = text.replace("cycles=LONG\n", "cycles=SHORT\n", 1)
        text = text.replace("cycles=LONG_RECOVERY\n", "cycles=SHORT_RECOVERY\n", 1)
    elif variant != "normal":
        raise ValueError(variant)
    return text


def image():
    return assemble(source())
