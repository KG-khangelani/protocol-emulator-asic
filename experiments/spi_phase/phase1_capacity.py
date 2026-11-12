# SPDX-License-Identifier: Apache-2.0
"""Declared phase-1 schedule family; oversized programs are reference-only."""
from itertools import combinations, permutations, product
from time import monotonic
from experiments.spi_phase.four_mode_programs import (
    ReferenceOnlyMachine, image, execute_reference, describe)
from tools.m1_contract_model import Instruction, State
from tools.spi_four_mode_oracle import timing, raw_at, assess


def best_reference(mode, order):
    if mode not in (1, 3):
        raise ValueError("phase-1 mode required")
    program, _ = image(mode, order, "held")
    return program[1:] if mode == 1 else program


def first_cs(program, tx=0x96):
    machine = ReferenceOnlyMachine()
    machine.edge(program, rst_n=False, ena=False)
    for n in range(1, 513):
        machine.edge(program, tx_payload=tx)
        resolved = (machine.gpio_value & machine.gpio_oe) | (8 & ~machine.gpio_oe)
        if not resolved & 8:
            return n
        if machine.state in (State.HALT, State.FAULT):
            return None
    raise RuntimeError("CS discovery exceeded declared finite horizon")


def evaluate(program, mode, order, rx=0x69, tx=0x96, profile="held", responses=None):
    cs = first_cs(program, tx)
    schedule = timing(mode, cs if cs is not None else 1)
    raw = {n: raw_at(n, schedule, rx, order, profile, responses)
           for n in range(-1, schedule["halt"]+1)}
    trace, commits = execute_reference(program, tx=tx, raw=raw.__getitem__,
                                       steps=schedule["halt"])
    captures = [s+24 for s in schedule["sample"]]
    errors = assess(trace, schedule, tx, rx, order, captures)
    if cs is None:
        errors.append({"kind": "missing_cs", "edge": 0})
    return {"mode": mode, "order": order, "tx": tx, "rx": rx, "profile": profile,
            **describe(program), "cs": cs, "schedule": schedule, "commits": commits,
            "accepted": not errors, "error_kinds": sorted({e["kind"] for e in errors}),
            "first_errors": errors[:4]}, trace


def deletions(mode, order):
    original = best_reference(mode, order)
    for removed in combinations(range(len(original)), len(original)-8):
        program = [w for i, w in enumerate(original) if i not in removed]
        yield "m%d-o%d-drop-%s" % (mode, order, "-".join(map(str, removed))), program, removed


def body_shapes():
    counts, accepted = {}, []
    for sequence in permutations("DWKS"):
        for wait, sample in product(range(50), repeat=2):
            n, events = 0, {}
            for op in sequence:
                n += 1
                if op == "W": n += wait
                elif op == "S":
                    n += sample
                    events["capture"] = n
                else: events[op] = n
            if events["capture"] < events["D"]:
                reason = "capture_before_first_drive"
            elif events["K"]-events["D"] != 25:
                reason = "wrong_leading_to_trailing_gap"
            elif not 2 <= events["capture"]-events["K"] <= 24:
                reason = "capture_outside_declared_hold_band"
            elif n != 50:
                reason = "wrong_bit_period"
            else:
                reason = "retained"
                accepted.append(("".join(sequence), wait, sample))
            counts[reason] = counts.get(reason, 0)+1
    return counts, accepted


def prefixes():
    for length in range(4):
        for tokens in product(("I", "A", "W"), repeat=length):
            if tokens.count("W") > 1:
                continue
            for delay in range(50) if "W" in tokens else (0,):
                yield tokens, delay


def construct(mode, order, tokens, delay, shape, drive_cs, set_cs):
    cpol = mode >> 1
    instructions = {
        "I": Instruction("SET", mask=12, value=8 | (cpol << 2), oe=12),
        "A": Instruction("SET", mask=12, value=cpol << 2, oe=12),
        "W": Instruction("WAIT", count=delay),
    }
    sequence, wait, sample = shape
    body = {
        "D": Instruction("DRIVE", mask=12 if drive_cs else 4, value=(1-cpol) << 2,
                         tx_pin=0, rx_pin=1, msb_first=order),
        "W": Instruction("WAIT", count=wait),
        "K": Instruction("SET", mask=12 if set_cs else 4, value=cpol << 2,
                         oe=12 if set_cs else 4),
        "S": Instruction("SAMPLE", count=sample, tx_pin=0, rx_pin=1, msb_first=order),
    }
    return [instructions[t] for t in tokens]+[Instruction("LOOP", length=4, count=8)]+[
        body[t] for t in sequence]+[instructions["I"], Instruction("HALT")]


def search(seconds=180):
    start = monotonic()
    filtered, shapes = body_shapes()
    prefix_list = list(prefixes())
    counts, accepted, failures = {}, [], {}
    for mode in (1, 3):
        for shape in shapes:
            for drive_cs, set_cs in product((False, True), repeat=2):
                for tokens, delay in prefix_list:
                    if monotonic()-start > seconds:
                        raise TimeoutError("fixed family-search budget exceeded")
                    program = construct(mode, 1, tokens, delay, shape, drive_cs, set_cs)
                    record, _ = evaluate(program, mode, 1)
                    key = f"mode{mode}-words{len(program)}"
                    counts.setdefault(key, {"tested": 0, "accepted": 0})
                    counts[key]["tested"] += 1
                    counts[key]["accepted"] += int(record["accepted"])
                    if record["accepted"]:
                        accepted.append({**record, "prefix": list(tokens), "prefix_wait": delay,
                                         "body": shape, "drive_updates_cs": drive_cs,
                                         "set_updates_cs": set_cs})
                    else:
                        for reason in record["error_kinds"]:
                            failures[reason] = failures.get(reason, 0)+1
    minimum = {str(mode): min(r["words"] for r in accepted if r["mode"] == mode)
               for mode in (1, 3)}
    return {"timing_layouts_examined": sum(filtered.values()),
            "timing_filter": filtered, "retained_timing_shapes": shapes,
            "gpio_variants_per_shape": 4, "prefix_count": len(prefix_list),
            "reference_candidates": sum(c["tested"] for c in counts.values()),
            "counts": counts, "accepted": accepted, "rejection_kinds": failures,
            "family_minimum_words": minimum, "global_minimum_proved": False,
            "seconds": round(monotonic()-start, 3), "wall_limit": seconds}
