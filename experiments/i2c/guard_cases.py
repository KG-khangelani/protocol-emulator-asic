# SPDX-License-Identifier: Apache-2.0
"""Public schedules and frozen historical inputs for the I²C guard comparison."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PANEL = ROOT / "evidence/E0049-review-council/panel-b"
sys.path.insert(0, str(ROOT))
from tools.i2c_oracle import Transaction

SOURCE = ROOT / "programs/od128-sram-v1/i2c_write_read.asm"
BASE = Transaction(kind="write_read", address=0x2e, tx=0x96, rx=0x01)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def reference():
    rows = (PANEL / "results/retime-cases.jsonl").read_bytes()
    prior = json.loads((PANEL / "results/retime.json").read_bytes())
    if digest(rows) != prior["cases_sha256"]:
        raise ValueError("council record digest differs")
    result = {row["test"]: row for row in map(json.loads, rows.splitlines())}
    if len(result) != 159:
        raise ValueError("council case inventory differs")
    return result


def programs():
    # Reuse the very assembler transform that produced the historical images.
    sys.path.insert(0, str(PANEL / "sources"))
    from retime_screen import retime
    from tools.assembler import assemble
    original = SOURCE.read_text(encoding="utf-8")
    variants = {k: assemble(retime(original, k) if k else original) for k in (0, 8, 24, 170, 171)}
    historic = json.loads((PANEL / "results/retime.json").read_bytes())["images"]
    for k, expected in historic.items():
        if variants[int(k)]["binary_sha256"] != expected["binary_sha256"]:
            raise ValueError("guard binary differs from council")
    return variants


def cases():
    for clocks in (0, 24, 8, 170, 171):
        yield f"plain-{clocks}", clocks, BASE, {}, f"plain-{clocks}" if clocks else None
    for clocks in (0, 24):
        for where in ("address", "data", "read_address"):
            label = "nack-" + where
            yield f"{clocks}-{label}", clocks, replace(BASE, nack=where), {}, label if clocks else None
        for pos in range(1, 39):
            for label, delay in (("before", 199987), ("final", 199991), ("late", 199992), ("forever", None)):
                key = f"{label}-{pos}"
                target = replace(BASE, timeout_release=pos if label in ("late","forever") else None)
                yield f"{clocks}-{key}", clocks, target, {pos:delay}, key if clocks else None
        for address in (0x08, 0x2e, 0x52, 0x77):
            for tx in (0x00, 0xff, 0x55, 0xaa):
                yield f"{clocks}-data-{address:02x}-{tx:02x}", clocks, replace(BASE,address=address,tx=tx,rx=tx^255), {}, None
