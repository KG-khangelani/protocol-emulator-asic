# SPDX-License-Identifier: Apache-2.0
"""Score all operating modes on one configured SM and one unchanged memory object."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess

from spi_program import resident_source
from tools.spi_four_mode_oracle import assess, timing


def rearm_sequence(tool_dir, words):
    entries = resident_source()[1]
    cases = []
    schedules = []
    for order in (0, 1):
        for mode in range(4):
            tx, rx = (0x3c, 0xa7) if mode & 1 else (0x96, 0x69)
            schedule = timing(mode, 2 if mode & 1 else 3)
            schedules.append(schedule)
            cases.append({"cpol": mode >> 1, "order": order, "wrongPolarity": False, "tx": tx, "words": words,
                          "primed": True, "finish": schedule["halt"], "inputStages": 3, "outputStages": 1,
                          "bypass": False, "manualPush": False, "entry": entries[mode & 1], "retainHost": True,
                          "peer": {"mode": mode, "rx": rx, "delays": [1, 96, 16, 80, 24, 72, 32, 64]}})
    simulator = Path(__file__).with_name("pio_spi_trace.cjs")
    run = subprocess.run(["node", str(simulator), str(tool_dir)], input=json.dumps({"batch": cases}),
                         text=True, capture_output=True, timeout=30)
    if run.returncode:
        raise ValueError("resident sequence failed: " + run.stderr[-1000:])
    measurements = json.loads(run.stdout)
    if len(measurements) != len(cases):
        raise ValueError("incomplete resident sequence")
    observations = []
    for index, (test, schedule, measured) in enumerate(zip(cases, schedules, measurements)):
        expected = test["peer"]
        target = measured["peerResult"]
        if target["decoded"] != test["tx"] or target["samples"] != schedule["sample"] or target["launches"] != schedule["launch"]:
            raise ValueError(f"resident target trace mismatch in transaction {index}")
        if not measured["stable"] or not measured["afterPopEmpty"] or measured["receiveByte"] != expected["rx"]:
            raise ValueError(f"stale RX or unstable completion in transaction {index}")
        raw = [int(digit) for digit in measured["targetRaw"]]
        trace = base64.b64decode(measured["publicRows"])
        rows = []
        for edge in range(schedule["halt"] + 1):
            out, enable, flags = trace[3 * edge:3 * edge + 3]
            valid = int(bool(flags & 1))
            rows.append({"edge": edge, "out": out, "oe": enable, "miso": raw[edge], "rx_valid": valid,
                         "rx": measured["receiveByte"] if valid else 0, "state": "HALT" if flags & 2 else "RUN"})
        captures = [edge + 3 for edge in schedule["sample"]]
        errors = assess(rows, schedule, test["tx"], expected["rx"], test["order"], captures)
        if errors:
            raise ValueError(f"resident mode wire check {index}: {errors[:1]}")
        groups = measured["counts"]
        if index and any(name in groups for name in ("program", "readback_jump", "readback_word")):
            raise ValueError("trusted resident image was rewritten or reread")
        if index and (groups.get("release_previous_dirs") != 1 or groups.get("previous_fstat") != 1):
            raise ValueError("no safe prior-result/state check")
        observations.append({"index": index, "mode": expected["mode"], "order": test["order"], "tx": test["tx"],
                             "expected_rx": expected["rx"], "observed_rx": measured["receiveByte"],
                             "entry": test["entry"], "setup_mmio": measured["setupCount"], "host_counts": groups,
                             "target": target, "wire_fifo_irq_sha256": hashlib.sha256(trace).hexdigest(),
                             "terminal_irq_edge": schedule["halt"], "fifo_valid_edge": captures[-1],
                             "operations": measured["operations"]})
    return observations
