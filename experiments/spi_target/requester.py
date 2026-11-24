"""External mode-0 stimulus and a public-pin judge shared by all targets."""
from bisect import bisect_right


REPLIES = {0xA4: 0x3C, 0xA5: 0xA7}


def scenario(command, half=500, phase=7, mode="normal", abort_bit=0, polarity=1):
    changes = {0: 4}
    frames = []
    select = 200 + phase
    for frame_index in range(2 if mode == "reselect" else 1):
        opcode = command if not frame_index else command ^ 1
        test = mode if not frame_index else "normal"
        frame = dict(command=opcode, select=select, rises=[], falls=[], mode=test)
        frames.append(frame)
        cs = 0
        time = select
        for bit in range(16):
            word = opcode if bit < 8 else 0x69
            mosi = (word >> (7 - bit % 8)) & 1
            changes[time] = cs | (mosi << 1)
            low = 250 + ((bit * 3 + 1) % 13) * 50 if test == "uneven" else half
            high = 250 + ((bit * 5 + 2) % 13) * 50 if test == "uneven" else half
            if bit == 0:
                low = 3000 if test == "late" else 300
                if test == "late":
                    frame["lost_clock"] = select
            if test in ("missing", "missing_reply") and bit == (4 if test == "missing" else 10):
                frame["lost_clock"] = time
                low += 3000
            if test == "pause" and bit == 8 + abort_bit and not polarity:
                frame["lost_clock"] = time
                low += 3000
            abort_here = test in ("reselect", "hold") and bit == 8 + abort_bit
            if abort_here and not polarity:
                time += 140
                break
            time += low
            changes[time] = cs | (mosi << 1) | 1
            frame["rises"].append(time)
            if abort_here:
                time += 140
                break
            if test == "pause" and bit == 8 + abort_bit and polarity:
                frame["lost_clock"] = time
                high += 3000
            if bit == 3 and test == "early":
                frame["early"] = time + 140
                cs = 4
                changes[time + 140] = cs | (mosi << 1) | 1
            time += high
            changes[time] = cs | (mosi << 1)
            frame["falls"].append(time)
        if test in ("reselect", "hold"):
            changes[time] = 4 | (mosi << 1) | polarity
            frame.update(abort=time, bit=abort_bit, polarity=polarity)
            if test == "reselect" and polarity:
                changes[time + 80] = 4 | (mosi << 1)
            select = time + 160
        elif test == "stuck_select":
            frame["lost_select"] = time
        else:
            time += 300
            changes[time] = 4 | (mosi << 1)
        frame["end"] = time
    return dict(events=sorted(changes.items()), frames=frames, finish=time + 2600)


def matrix():
    for opcode in range(256):
        yield f"opcode-{opcode:02x}", scenario(opcode)
    for opcode in REPLIES:
        for half in (250, 500, 1000):
            for phase in (1, 7, 13, 19):
                yield f"normal-{opcode:02x}-{half}-{phase}", scenario(opcode, half, phase)
                for bit in range(8):
                    for polarity in (0, 1):
                        yield (f"reselect-{opcode:02x}-{half}-{phase}-{bit}-{polarity}",
                               scenario(opcode, half, phase, "reselect", bit, polarity))
        for bit in range(8):
            for polarity in (0, 1):
                yield f"hold-{opcode:02x}-{bit}-{polarity}", scenario(opcode, 250, 7, "hold", bit, polarity)
                yield f"pause-{opcode:02x}-{bit}-{polarity}", scenario(opcode, 250, 7, "pause", bit, polarity)
        yield f"uneven-{opcode:02x}", scenario(opcode, 500, 13, "uneven")
        yield f"stuck-select-{opcode:02x}", scenario(opcode, 500, 7, "stuck_select")
    for mode in ("missing", "missing_reply", "late", "early"):
        yield mode, scenario(0xA5, 500, 7, mode)


def validate_stimulus(case):
    events = case["events"]
    times = [r[0] for r in events]
    if times != sorted(set(times)) or list(events[0]) != [0, 4] or any(v not in range(8) for _, v in events):
        raise ValueError("invalid requester input events")
    def state(t):
        return events[bisect_right(times, t) - 1][1]
    for i, frame in enumerate(case["frames"]):
        start, end = frame["select"], frame["end"]
        transitions = [(t, v & 1) for t, v in events if start < t <= end and (v ^ state(t - 1)) & 1]
        if ([t for t, level in transitions if level] != frame["rises"]
            or [t for t, level in transitions if not level] != frame["falls"]):
            raise ValueError("clock edges disagree with frame")
        rises = frame["rises"]
        data = sum(((state(t) >> 1) & 1) << (7 - n) for n, t in enumerate(rises[:8]))
        if data != frame["command"] or rises[0] - start < 300 or state(start) & 5 or not state(start - 1) & 4:
            raise ValueError("incorrect command or selection stimulus")
        if "abort" in frame:
            abort = frame["abort"]
            if state(abort) & 5 != 4 | frame["polarity"] or state(abort - 1) & 4:
                raise ValueError("incorrect abort stimulus")
            if frame["mode"] == "reselect":
                fresh = case["frames"][i + 1]
                if (fresh["select"] != abort + 160 or fresh["rises"][0] != fresh["select"] + 300
                    or fresh["command"] != (data ^ 1) or state(abort + 79) & 1 != frame["polarity"]
                    or state(abort + 80) & 5 != 4
                    or any(not v & 4 for t, v in events if abort <= t < fresh["select"])):
                    raise ValueError("incorrect fresh frame stimulus")
            elif any(t > abort for t in times):
                raise ValueError("clock changed in held-abort observation")


class Trace:
    """Rows contain nanoseconds, output enables, resolved MISO, marker and terminal."""

    def __init__(self, rows, end):
        if not rows or rows[0][0] != 0:
            raise ValueError("initial pin state missing")
        self.rows = rows
        self.times = [r[0] for r in rows]
        self.end = end
        if self.times != sorted(set(self.times)) or self.times[-1] > end:
            raise ValueError("unordered or out-of-window observations")
        if any(oe & ~0x38 or m not in (0, 1) or k not in range(4) or halt not in (0, 1)
               or (not oe & 8 and m) for _, oe, m, k, halt in rows):
            raise ValueError("invalid public pin observation")

    def at(self, time):
        return self.rows[bisect_right(self.times, time) - 1]

    def interval(self, lo, hi):
        yield [lo, *self.at(lo)[1:]]
        yield from self.rows[bisect_right(self.times, lo):bisect_right(self.times, hi)]


def score(case, rows):
    validate_stimulus(case)
    trace = Trace(rows, case["finish"])
    errors, replies, releases, normal_releases, setups, holds = [], [], [], [], [], []

    def issue(kind, when, observed):
        errors.append(dict(check=kind, ns=when, observed=observed))

    def quiet(lo, hi, label):
        active = next((r for r in trace.interval(lo, hi) if r[1] & 8), None)
        if active:
            issue(label, active[0], active)

    def terminal(earliest, deadline, expected):
        seen = next((r for r in rows if r[4]), None)
        if not seen:
            issue("terminal_missing", deadline, trace.at(deadline))
        elif seen[0] < earliest or seen[0] > deadline or seen[3] != expected or seen[1] & 0x38 != 0x30:
            issue("terminal_result", min(seen[0], deadline), seen)
        elif any((r[1] & 0x38, r[3], r[4]) != (0x30, expected, 1)
                 for r in trace.interval(seen[0], case["finish"])):
            issue("terminal_unstable", seen[0], seen)

    signal = []
    for t, oe, wire, _, _ in rows:
        state = wire if oe & 8 else None
        if not signal or signal[-1][1] != state:
            signal.append((t, state))
    signal_times = [v[0] for v in signal]
    for index, frame in enumerate(case["frames"]):
        opcode, mode = frame["command"], frame["mode"]
        rises, falls = frame["rises"], frame["falls"]
        quiet(frame["select"], falls[7] - 1, "fresh_prefix_drive" if index else "prefix_drive")
        if mode in ("missing", "late", "early") or opcode not in REPLIES:
            quiet(frame["select"], case["finish"], "rejected_command_driven")
            if mode == "early":
                terminal(frame["early"], case["finish"], 2)
            elif mode in ("missing", "late"):
                terminal(frame["lost_clock"], frame["lost_clock"] + 2000, 3)
            else:
                bad_bit = next(i for i in range(7) if (opcode ^ 0xA4) & (1 << (7 - i)))
                terminal(rises[bad_bit], case["finish"], 2)
                if not trace.at(rises[bad_bit + 1] - 1)[4]:
                    issue("late_prefix_rejection", rises[bad_bit + 1] - 1, trace.at(rises[bad_bit + 1] - 1))
            continue
        if mode in ("missing_reply", "pause"):
            terminal(frame["lost_clock"], frame["lost_clock"] + 2000, 3)
            quiet(frame["lost_clock"] + 2000, case["finish"], "missing_reply_drive")
        decoded = 0
        good_bits = 0
        for bit, rise in enumerate(rises[8:]):
            if mode in ("missing_reply", "pause") and rise > frame["lost_clock"]:
                break
            expected = REPLIES[opcode] >> (7 - bit) & 1
            at = trace.at(rise)
            k = bisect_right(signal_times, rise) - 1
            if (at[1] & 8) and at[2] == expected:
                setup = rise - signal[k][0]
                next_change = signal[k + 1][0] if k + 1 < len(signal) else trace.end + 1
                hold = next_change - rise
                setups.append(setup)
                holds.append(hold)
                if setup < 60 or hold < 40:
                    issue("reply_setup_hold", rise, [setup, hold])
                else:
                    good_bits += 1
            else:
                issue("reply_bit", rise, [bit, expected, at])
            decoded = (decoded << 1) | at[2]
        if good_bits == 8 and mode not in ("hold", "reselect", "pause", "missing_reply", "stuck_select"):
            replies.append(decoded)
        if mode in ("missing_reply", "pause"):
            continue
        if "abort" in frame:
            origin = frame["abort"]
            expected = REPLIES[opcode] >> (7 - frame["bit"]) & 1
            prior = trace.at(origin - 1)
            if not prior[1] & 8 or prior[2] != expected:
                issue("abort_not_driven", origin - 1, prior)
            release = next((r[0] for r in rows if r[0] >= origin and not r[1] & 8), None)
            active = bool(prior[1] & 8) and prior[2] == expected
            latency = release - origin if active and release is not None else None
            releases.append(latency)
            if latency is None or latency > 160:
                issue("abort_release", origin + 160, latency)
            else:
                end = case["frames"][index + 1]["select"] if mode == "reselect" else case["finish"]
                quiet(release, end, "drive_after_abort")
        else:
            origin = falls[-1]
            release = next((r[0] for r in rows if r[0] >= origin and not r[1] & 8), None)
            latency = release - origin if release is not None and trace.at(origin - 1)[1] & 8 else None
            normal_releases.append(latency)
            if latency is None or latency > 160:
                issue("normal_release", origin + 160, latency)
            else:
                quiet(release, case["finish"], "drive_after_completion")
            if mode == "stuck_select":
                terminal(frame["lost_select"], frame["lost_select"] + 2000, 3)
            else:
                terminal(frame["end"], case["finish"], 1)
    return dict(errors=sorted(errors, key=lambda e: e["ns"]), replies=replies, abort_ns=releases,
                normal_release_ns=normal_releases, min_setup_ns=min(setups, default=None),
                min_hold_ns=min(holds, default=None))
