"""Additional externally scheduled SPI edges, independent of the candidate program."""
from copy import deepcopy
from random import Random
from requester import REPLIES, Trace, scenario, score


def retime(case, seed, *, varied_widths=False, abort_offset=140, stretch=None):
    """Change half-cycle durations and dummy bits while preserving select spacing."""
    rng = Random(seed)
    widths = (250, 271, 333, 499, 628, 891, 997, 1000)
    durations = {}
    dummy_at = {}
    for frame in case["frames"]:
        dummy = rng.randrange(256)
        for i, t in enumerate(frame["rises"]):
            if i and varied_widths:
                durations[t] = rng.choice(widths)
        for i, t in enumerate(frame["falls"]):
            if varied_widths:
                durations[t] = rng.choice(widths)
            if 7 <= i < 15:
                dummy_at[t] = (dummy >> (14 - i)) & 1
        if "abort" in frame:
            durations[frame["abort"]] = abort_offset
    if stretch:
        edge, width = stretch
        durations[edge] = width
    mapping = {0: 0}
    after, before, dummy = 0, 0, None
    selects = {f["select"] for f in case["frames"]}
    changed = []
    for t, value in case["events"]:
        after += durations.get(t, t - before)
        mapping[t] = after
        before = t
        if t in selects:
            dummy = None
        if t in dummy_at:
            dummy = dummy_at[t]
        if dummy is not None:
            value = (value & ~2) | (dummy << 1)
        changed.append([after, value])
    output = deepcopy(case)
    output["events"] = changed
    output["finish"] = after + case["finish"] - before
    for frame in output["frames"]:
        for key in ("select", "end", "abort", "lost_clock"):
            if key in frame:
                frame[key] = mapping[frame[key]]
        for key in ("rises", "falls"):
            frame[key] = [mapping[t] for t in frame[key]]
    return output


def extra_cases():
    for command in REPLIES:
        for bit in range(8):
            for polarity in (0, 1):
                seed = command * 1000 + bit * 100 + polarity * 20
                for phase in range(20):
                    base = scenario(command, 250, phase, "reselect", bit, polarity)
                    yield (f"varied-{command:02x}-{bit}-{polarity}-{phase}",
                           retime(base, seed + phase, varied_widths=True, abort_offset=150 + (seed + phase) % 89))
                # Before the first drive there is no active target branch to time.
                if bit or polarity:
                    for phase in (1, 7, 13, 19):
                        base = scenario(command, 250, phase, "reselect", bit, polarity)
                        for offset in (1, 19, 41, 65, 99, 139, 199, 241):
                            yield (f"edge-{command:02x}-{bit}-{polarity}-{phase}-{offset}",
                                   retime(base, seed + phase + offset, abort_offset=offset))
                base = scenario(command, 250, 7)
                frame = base["frames"][0]
                origin = frame["rises"][8 + bit] if polarity else frame["falls"][7 + bit]
                next_edge = frame["falls"][8 + bit] if polarity else frame["rises"][8 + bit]
                for width in (1000, 1200, 1280, 1320, 1360, 1400, 1440, 1480, 1600, 2000, 3000):
                    case = retime(base, seed + width, stretch=(next_edge, width))
                    case["stretch"] = {"origin": origin, "width": width}
                    yield f"boundary-{command:02x}-{bit}-{polarity}-{width}", case


def edge_ties():
    """Move an otherwise identical requester 2 ns either side of a core-edge abort."""
    for command in REPLIES:
        for bit in range(1, 8):
            # Match the dummy data in the original phase-19 early abort.
            seed = command * 1000 + bit * 100 + 20
            for phase in (17, 19, 21):
                base = scenario(command, 250, phase, "reselect", bit, 0)
                yield f"edge-{command:02x}-{bit}-0-{phase}-1", retime(base, seed, abort_offset=1)


def marker_errors(rows, finish):
    # The existing SET publishes the terminal marker one clock before HALT.
    first = next((r for r in rows if r[1] & 0x30 or r[3]), None)
    if first is None:
        return []
    trace = Trace(rows, finish)
    expected = (0x30, first[3])
    if not first[3] or any((r[1] & 0x30, r[3]) != expected for r in trace.interval(first[0], finish)):
        return [{"check": "marker_used_before_terminal", "ns": first[0], "observed": first}]
    halted = next((r for r in rows if r[4]), None)
    if halted is None or not 0 <= halted[0] - first[0] <= 20:
        return [{"check": "marker_without_terminal", "ns": first[0], "observed": halted}]
    return []


def assess(name, case, rows):
    judged = score(case, rows)
    frame = case["frames"][0]
    if name.startswith("edge-"):
        # At an early falling-edge abort a new data bit need not yet be valid.
        # The preceding or next bit can be active. Time actual output disable
        # and still impose every original command, sample and fresh-frame check.
        origin, bit = frame["abort"], frame["bit"]
        trace = Trace(rows, case["finish"])
        before = trace.at(origin - 1)
        current = REPLIES[frame["command"]] >> (7 - bit) & 1
        allowed = {current}
        if not frame["polarity"] and bit:
            allowed.add(REPLIES[frame["command"]] >> (8 - bit) & 1)
        errors = [e for e in judged["errors"] if e["check"] not in ("abort_not_driven", "abort_release")]
        release = next((r[0] for r in rows if r[0] >= origin and not r[1] & 8), None)
        latency = None if release is None or not before[1] & 8 else release - origin
        if latency is None or latency > 160 or before[2] not in allowed:
            errors.append(dict(check="active_branch_release", ns=origin + 160, observed=[before, latency]))
        elif any(r[1] & 8 for r in trace.interval(release, case["frames"][1]["select"])):
            errors.append(dict(check="reasserted_after_release", ns=release, observed=latency))
        judged.update(errors=errors, abort_ns=[latency])
    if name.startswith("boundary-"):
        origin, width = case["stretch"]["origin"], case["stretch"]["width"]
        timeout_case = deepcopy(case)
        timeout_case["frames"][0].update(mode="pause", lost_clock=origin)
        timeout = score(timeout_case, rows)
        if not judged["errors"]:
            judged["boundary_outcome"] = "delivered"
            if width >= 2000:
                judged["errors"].append(dict(check="accepted_after_watchdog", ns=origin + 2000, observed=width))
        elif not timeout["errors"]:
            judged = timeout
            judged["boundary_outcome"] = "timeout"
            if width <= 1000:
                judged["errors"].append(dict(check="timed_out_legal_clock", ns=origin + width, observed=width))
        else:
            judged["boundary_outcome"] = "neither"
    judged["errors"] += marker_errors(rows, case["finish"])
    origin = frame.get("lost_clock", case.get("stretch", {}).get("origin"))
    terminal = next((r for r in rows if r[4]), None)
    if origin is not None and terminal and terminal[3] == 3:
        judged["timeout_ns"] = terminal[0] - origin
    return judged
