# SPDX-License-Identifier: Apache-2.0
"""Independent SPI pin mathematics: no instruction, executor or RTL imports."""


def validate(mode, order, half=25):
    if type(mode) is not int or mode not in range(4):
        raise ValueError("mode must be 0..3")
    if type(order) is not int or order not in (0, 1):
        raise ValueError("order must be binary")
    if type(half) is not int or half < 4:
        raise ValueError("half period must be at least four core ticks")


def bit(byte, index, order):
    if not 0 <= byte <= 255 or not 0 <= index < 8 or order not in (0, 1):
        raise ValueError("invalid byte, index or order")
    return (byte >> (7-index if order else index)) & 1


def timing(mode, cs_edge, half=25):
    validate(mode, 0, half)
    if type(cs_edge) is not int or cs_edge < 1:
        raise ValueError("CS needs a preceding idle interval, including [0,1]")
    leading = [cs_edge+half+2*half*j for j in range(8)]
    trailing = [n+half for n in leading]
    sample = trailing if mode & 1 else leading
    launch = leading if mode & 1 else [cs_edge+2*half*j for j in range(8)]
    release = max(trailing[-1], sample[-1]+half)
    return {"mode": mode, "cpol": mode >> 1, "cpha": mode & 1, "half": half,
            "cs": cs_edge, "leading": leading, "trailing": trailing,
            "sample": sample, "launch": launch, "release": release, "halt": release+1}


def raw_at(edge, schedule, rx, order, profile, responses=None):
    validate(schedule["mode"], order, schedule["half"])
    if profile == "held":
        responses = responses if responses is not None else [96]*8
        if len(responses) != 8 or any(type(d) is not int or not 1 <= d <= 4*schedule["half"]-4 for d in responses):
            raise ValueError("invalid quarter-tick response profile")
        value = 1
        for j, launch in enumerate(schedule["launch"]):
            if 4*edge >= 4*launch+responses[j]:
                value = bit(rx, j, order)
        return value
    if profile == "edge_only":
        active = [j for j, launch in enumerate(schedule["launch"]) if edge >= launch]
        if not active:
            return 1
        j = active[-1]
        intended = bit(rx, j, order)
        return intended if edge == schedule["sample"][j] else 1-intended
    raise ValueError("unknown input profile")


def wire_value(edge, schedule, tx, order):
    """Expected resolved wire vector, after a core edge during the transaction."""
    cpol = schedule["cpol"]
    sck = cpol
    if any(a <= edge < b for a, b in zip(schedule["leading"], schedule["trailing"])):
        sck = 1-cpol
    launched = [j for j, n in enumerate(schedule["launch"]) if edge >= n]
    mosi = bit(tx, launched[-1], order) if launched else 0
    cs = int(edge < schedule["cs"] or edge >= schedule["release"])
    return (cs << 3) | (sck << 2) | mosi


def assess(trace, schedule, tx, rx, order, capture):
    """Judge externally observable-style rows against pin equations, not opcodes."""
    errors = []
    rows = {r["edge"]: r for r in trace}
    if len(rows) != len(trace) or set(rows) != set(range(schedule["halt"]+1)):
        return [{"kind": "trace_extent", "edge": -1}]
    cs = schedule["cs"]
    before = rows[cs-1]
    resolved = lambda r: (r["out"] & r["oe"]) | (8 & ~r["oe"])
    if ((resolved(before) >> 2) & 1) != schedule["cpol"]:
        errors.append({"kind": "idle_before_cs", "edge": cs-1})
    for n, row in rows.items():
        if row["oe"] & 2:
            errors.append({"kind": "miso_contention", "edge": n})
        if n < cs and not (resolved(row) & 8):
            errors.append({"kind": "premature_cs", "edge": n})
        if n >= cs:
            expected = wire_value(n, schedule, tx, order)
            # CPHA1 MOSI is unconstrained until the first launch.
            mask = 0xFE if n < schedule["launch"][0] else 0xFF
            if (resolved(row) & mask) != (expected & mask):
                errors.append({"kind": "pins", "edge": n, "actual": resolved(row), "expected": expected})
            required = 12 if n < schedule["launch"][0] else 13
            if row["oe"] != required:
                errors.append({"kind": "direction", "edge": n})
        if row["state"] == "FAULT" or (row["state"] == "HALT" and n < schedule["halt"]):
            errors.append({"kind": "terminal_timing", "edge": n})
        if row["rx_valid"] != int(n >= capture[-1]):
            errors.append({"kind": "valid_timing", "edge": n})
        if row["rx"] != (rx if n >= capture[-1] else 0):
            errors.append({"kind": "received_byte", "edge": n, "actual": row["rx"], "expected": rx})
    if rows[schedule["halt"]]["state"] != "HALT":
        errors.append({"kind": "missing_halt", "edge": schedule["halt"]})
    for j, n in enumerate(schedule["sample"]):
        if (resolved(rows[n]) & 1) != bit(tx, j, order):
            errors.append({"kind": "wire_mosi", "edge": n})
        if rows[n]["miso"] != bit(rx, j, order):
            errors.append({"kind": "wire_miso", "edge": n})
    return errors
