# SPDX-License-Identifier: Apache-2.0
"""G2 digital I2C acceptance from public events; no ISA/model/fixture imports.

Time is in 5 ns ticks. Rows are post-event observations, with every public
transition retained. The adapter must obtain state/RX/valid from public uo_out
selectors, not hierarchical executor signals. See p-i2c-controller-100k.md.
"""
from dataclasses import dataclass

CORE = 4
LOW = 940
HIGH = 800
SETUP = 50
VALID_MAX = 690
START_SETUP = 940
START_HOLD = 800
STOP_SETUP = 800
BUS_FREE = 940
PERIOD = 2000
DEADLINE = 200000
CLEANUP = 64
OUTCOMES = {"OK": 1, "NACK": 2, "TIMEOUT": 3}


@dataclass(frozen=True)
class Transaction:
    kind: str = "write_read"
    address: int = 0x52
    tx: int = 0x96
    rx: int = 0x69
    # First address, write data, or repeated-START read address may be rejected.
    nack: str | None = None
    # One-based index of controller SCL release, including Sr/STOP preparation.
    timeout_release: int | None = None

    def __post_init__(self):
        if self.kind not in ("write", "read", "write_read"):
            raise ValueError("transaction must be write/read/write_read")
        if type(self.address) is not int or not 0x08 <= self.address <= 0x77:
            raise ValueError("ordinary 7-bit target address must be 0x08..0x77")
        if any(type(b) is not int or not 0 <= b <= 255 for b in (self.tx, self.rx)):
            raise ValueError("payload must be a byte")
        possible = {None, "address"}
        if self.kind != "read":
            possible.add("data")
        if self.kind == "write_read":
            possible.add("read_address")
        if self.nack not in possible:
            raise ValueError("NACK position is not part of this transaction")
        if self.timeout_release is not None and (
                type(self.timeout_release) is not int or self.timeout_release < 1):
            raise ValueError("timeout release must be a positive index")

    @property
    def outcome(self):
        return "TIMEOUT" if self.timeout_release else "NACK" if self.nack else "OK"


def observation_edge(raw_tick):
    """Post-edge raw transition -> first executor edge seeing two-flop input."""
    return CORE * (raw_tick // CORE + 3)


def _segments(case):
    """Expected wire bits and who owns SDA, derived only from transaction intent."""
    segments = [[]]

    def byte(value, owner, label):
        segments[-1].extend((int(c), owner, label) for c in f"{value:08b}")

    def ack(rejected, owner, label):
        segments[-1].append((int(rejected), owner, label))

    byte(case.address * 2 + int(case.kind == "read"), "controller", "address")
    ack(case.nack == "address", "target", "address_ack")
    if case.nack == "address":
        return segments
    if case.kind != "read":
        byte(case.tx, "controller", "write_data")
        ack(case.nack == "data", "target", "data_ack")
        if case.nack == "data" or case.kind == "write":
            return segments
        segments.append([])
        byte(case.address * 2 + 1, "controller", "read_address")
        ack(case.nack == "read_address", "target", "read_address_ack")
        if case.nack == "read_address":
            return segments
    byte(case.rx, "target", "read_data")
    ack(True, "controller", "final_nack")
    return segments


def assess(rows, case):
    """Return errors plus decoded observations. An empty error list is PASS.

    Events: t, out, oe (full controller GPIO), target_out/target_oe (two bus
    pins), bus (observed resolved two-bit bus), state, rx, rx_valid. Initial
    idle begins at t=0; raw-valid must have been invalidated by the host load.
    End row must include HALT and at least the required post-STOP bus-free time.
    """
    return _assess(rows, case)


def _assess(rows, case, *, prefix=False):
    errors = []
    events = []
    periods = []

    def fail(kind, tick, **details):
        errors.append({"kind": kind, "t": tick, **details})

    report = {"errors": errors, "events": events, "periods": periods,
              "outcome": case.outcome, "quantum_ns": 5}
    fields = {"t", "out", "oe", "target_out", "target_oe", "bus", "state", "rx", "rx_valid"}
    if not rows:
        fail("empty_trace", 0)
        return report
    for i, row in enumerate(rows):
        if not fields <= row.keys():
            fail("trace_schema", i)
            return report
        for field, maximum in (("out", 255), ("oe", 255), ("target_out", 3),
                               ("target_oe", 3), ("bus", 3), ("rx", 255), ("rx_valid", 1)):
            if type(row[field]) is not int or not 0 <= row[field] <= maximum:
                fail("trace_value", i, field=field)
                return report
        if type(row["t"]) is not int or row["t"] < 0 or (
                i and row["t"] <= rows[i - 1]["t"]) or row["state"] not in ("RUN", "WAIT", "HALT", "FAULT"):
            fail("trace_order_or_state", i)
            return report
    first = rows[0]
    if first["t"] != 0 or first["bus"] != 3 or (first["oe"] | first["target_oe"]) & 3:
        fail("initial_idle", first["t"])
    if first["rx_valid"]:
        fail("initial_stale_valid", 0)
    expected = _segments(case)
    maximum_releases = sum(map(len, expected)) + len(expected)
    if case.timeout_release and case.timeout_release > maximum_releases:
        fail("impossible_timeout_index", 0)
        return report
    # A generous finite transaction bound, not a claimed throughput minimum.
    if rows[-1]["t"] > 100000 + maximum_releases * DEADLINE + CLEANUP:
        fail("completion_bound", rows[-1]["t"])

    # Validate open-drain physics and terminal status over the whole trace.
    terminal = None
    for i, row in enumerate(rows):
        t = row["t"]
        if row["out"] & row["oe"] & 3:
            fail("controller_active_high", t)
        if row["target_out"] & row["target_oe"] & 3:
            fail("target_active_high", t)
        if row["bus"] != (3 & ~(row["oe"] | row["target_oe"])):
            fail("wired_and", t)
        marker = (row["out"] >> 2) & 7
        if row["oe"] & 0x1C != 0x1C or row["oe"] & 0xE0:
            fail("marker_direction", t)
        if marker not in (0, OUTCOMES[case.outcome]):
            fail("outcome_marker", t, actual=marker)
        if row["state"] == "FAULT":
            fail("unexpected_fault", t)
        if i and any(row[k] != rows[i-1][k] for k in ("out", "oe", "state", "rx", "rx_valid")) and t % CORE:
            fail("controller_off_edge", t)
        if row["state"] == "HALT" and terminal is None:
            terminal = row
        if terminal is not None and any(row[k] != terminal[k] for k in ("out", "oe", "state", "rx", "rx_valid")):
            fail("terminal_not_stable", t)
    if prefix:
        if terminal is not None or any((r["out"] >> 2) & 7 for r in rows):
            fail("completed_before_abort", rows[-1]["t"])
    elif terminal is None:
        fail("missing_halt", rows[-1]["t"])
    elif ((terminal["out"] >> 2) & 7) != OUTCOMES[case.outcome] or terminal["oe"] & 3:
        fail("terminal_outcome_or_release", terminal["t"])

    # Each release has its own deadline; raw-high on the final observation edge
    # wins. Inspect public direction while stretched, not just the flat wire.
    releases = []
    for i in range(1, len(rows)):
        before, row = rows[i-1], rows[i]
        if before["oe"] & 1 and not row["oe"] & 1:
            releases.append((i, row["t"]))
    deadline = None
    for number, (i, release) in enumerate(releases, 1):
        d = release + DEADLINE
        high_row = next((r for r in rows[i:] if r["bus"] & 1), None)
        observed = observation_edge(high_row["t"]) if high_row else None
        timed_out = observed is None or observed > d
        declared_timeout = number == case.timeout_release
        if declared_timeout:
            deadline = d
            if not timed_out:
                fail("premature_timeout", release, observation=observed, deadline=d)
        elif timed_out and not (prefix and rows[-1]["t"] < d):
            fail("unreported_timeout", release, deadline=d)
        until = d if timed_out else observed
        for row in rows[i:]:
            if row["t"] >= until:
                break
            if row["oe"] & 1 or (row["oe"] & 2) != (rows[i]["oe"] & 2):
                fail("advance_before_scl_observed", row["t"], release=number)
        if declared_timeout:
            if number != len(releases):
                fail("clocks_after_timeout", releases[number][1])
            break
    if case.timeout_release and not prefix:
        if deadline is None:
            fail("missing_timeout_release", rows[-1]["t"])
        else:
            marked = next((r for r in rows if (r["out"] >> 2) & 7), None)
            if marked is None or not deadline <= marked["t"] <= deadline + CLEANUP:
                fail("timeout_marker_deadline", marked["t"] if marked else rows[-1]["t"], deadline=deadline)
            if terminal is None or not deadline <= terminal["t"] <= deadline + CLEANUP:
                fail("timeout_cleanup_deadline", terminal["t"] if terminal else rows[-1]["t"], deadline=deadline)
    elif not prefix and len(releases) != maximum_releases:
        fail("clock_release_count", rows[-1]["t"], actual=len(releases), expected=maximum_releases)

    # Decode bits on falling edges. A START/STOP preparation rise has no data
    # falling edge and must not be misclassified as a spurious ninth/tenth bit.
    active = False
    stopped = None
    segment = -1
    count = 0
    pending = None
    start = None
    low = None
    high = None
    last_data_change = 0
    last_rise = None
    low_stretched = False
    for i in range(1, len(rows)):
        p, r = rows[i-1], rows[i]
        t = r["t"]
        if deadline is not None and t >= deadline:
            break  # Forced release is cleanup, never an accepted STOP.
        scl0, scl1 = p["bus"] & 1, r["bus"] & 1
        sda0, sda1 = (p["bus"] >> 1) & 1, (r["bus"] >> 1) & 1
        changed_sda = sda0 != sda1
        # Ordering margin is a project digital-screen rule, not analog proof.
        if changed_sda and scl0 != scl1:
            fail("simultaneous_clock_data", t)
        is_start = scl0 and scl1 and sda0 and not sda1
        is_stop = scl0 and scl1 and not sda0 and sda1
        if is_start or is_stop:
            if r["target_oe"] & 2 or (is_start and not r["oe"] & 2) or (is_stop and r["oe"] & 2):
                fail("boundary_owner", t)
            if is_start:
                if stopped is not None:
                    fail("start_after_stop", t)
                if not active:
                    if t < BUS_FREE:
                        fail("bus_free_before_start", t)
                else:
                    if high is None or t - high < START_SETUP:
                        fail("repeated_start_setup", t)
                    if count != len(expected[min(segment, len(expected)-1)]):
                        fail("segment_length", t, segment=segment, count=count)
                segment += 1
                if segment >= len(expected):
                    fail("extra_start", t)
                count = 0
                active = True
                start = t
                last_rise = None
                events.append({"kind": "START" if segment == 0 else "RESTART", "t": t})
            else:
                if not active:
                    fail("stop_without_start", t)
                if high is None or t - high < STOP_SETUP:
                    fail("stop_setup", t)
                if segment != len(expected)-1 or count != len(expected[min(max(segment, 0), len(expected)-1)]):
                    fail("segment_length", t, segment=segment, count=count)
                active = False
                stopped = t
                events.append({"kind": "STOP", "t": t})
            pending = None
        elif changed_sda:
            last_data_change = t
        if not scl0 and scl1:
            high = t
            if low is None or t-low < LOW:
                fail("scl_low", t)
            if t-last_data_change < SETUP:
                fail("data_setup", t)
            if low is not None and not low_stretched and last_data_change-low > VALID_MAX:
                fail("data_valid_delay", t)
            if active:
                pending = (sda1, bool(r["oe"] & 2), bool(r["target_oe"] & 2), t)
            else:
                fail("clock_outside_transaction", t)
        if scl0 and not scl1:
            if not r["oe"] & 1:
                fail("scl_owner", t)
            if start is not None:
                if t-start < START_HOLD:
                    fail("start_hold", t)
                start = None
            elif high is None or t-high < HIGH:
                fail("scl_high", t)
            if pending is not None:
                bit, controller, target, rise = pending
                if low is not None:
                    periods.append(t-low)
                    if t-low < PERIOD:
                        fail("clock_frequency", rise)
                if last_rise is not None:
                    periods.append(rise-last_rise)
                    if rise-last_rise < PERIOD:
                        fail("clock_frequency", rise)
                last_rise = rise
                if segment >= len(expected) or count >= len(expected[segment]):
                    fail("extra_clock", t)
                else:
                    want, owner, label = expected[segment][count]
                    if bit != want:
                        fail("wire_bit", rise, label=label, bit=count, actual=bit, expected=want)
                    if ((owner == "controller" and (target or controller != (not want))) or
                            (owner == "target" and (controller or target != (not want)))):
                        fail("sda_ownership", rise, label=label, bit=count)
                    events.append({"kind": "BIT", "t": rise, "segment": segment,
                                   "index": count, "value": bit, "label": label})
                count += 1
            pending = None
            low = t
            low_stretched = False
        if not scl1 and not r["oe"] & 1 and r["target_oe"] & 1:
            low_stretched = True
        if scl0 and scl1 and not (is_start or is_stop) and (
                (p["oe"] ^ r["oe"] | p["target_oe"] ^ r["target_oe"]) & 2):
            fail("sda_ownership_during_high", t)
        if stopped is not None and (r["bus"] != 3 or (r["oe"] | r["target_oe"]) & 3):
            fail("bus_not_free_after_stop", t)
    if not case.timeout_release and not prefix:
        if stopped is None:
            fail("missing_stop", rows[-1]["t"])
        else:
            marked = next((r for r in rows if (r["out"] >> 2) & 7), None)
            if marked is None or marked["t"] < stopped+BUS_FREE:
                fail("early_outcome", marked["t"] if marked else rows[-1]["t"])
            if terminal is None or terminal["t"] < stopped+BUS_FREE:
                fail("bus_free_before_halt", terminal["t"] if terminal else rows[-1]["t"])
        if case.outcome == "OK" and case.kind != "write" and terminal is not None:
            if not terminal["rx_valid"] or terminal["rx"] != case.rx:
                fail("received_byte", terminal["t"], actual=terminal["rx"], expected=case.rx)
    report["releases"] = len(releases)
    report["stop"] = stopped
    report["halt"] = terminal["t"] if terminal else None
    report["fastest_hz"] = 200000000 / min(periods) if periods else None
    return report


def assess_abort(rows, case, *, control, tick):
    """Explicit control intervention, never a successful protocol transaction.

    All rows also carry public rst_n/ena/load and target_isolated (0/1). The
    control starts at tick and stays asserted to the end of this finite trace.
    Loader target isolation takes effect before loader ownership at that event.
    Resume/reload needs a fresh separately judged transaction and input flush.
    """
    if control not in ("reset", "disable", "load") or type(tick) is not int or tick <= 0 or tick % CORE:
        raise ValueError("abort needs reset/disable/load on a positive core edge")
    if not rows or not any(r.get("t") == tick for r in rows):
        return {"errors": [{"kind": "missing_abort_event", "t": tick}], "outcome": "ABORT"}
    controls = ("rst_n", "ena", "load", "target_isolated")
    if any(any(type(r.get(k)) is not int or r[k] not in (0, 1) for k in controls) for r in rows):
        return {"errors": [{"kind": "abort_control_schema", "t": tick}], "outcome": "ABORT"}
    for i, row in enumerate(rows):
        if type(row.get("t")) is not int or (i and row["t"] <= rows[i-1]["t"]):
            return {"errors": [{"kind": "abort_trace_order", "t": tick}], "outcome": "ABORT"}
        if any(type(row.get(k)) is not int or not 0 <= row[k] <= maximum
               for k, maximum in (("out", 255), ("oe", 255), ("rx", 255),
                                  ("rx_valid", 1), ("target_oe", 3))):
            return {"errors": [{"kind": "abort_trace_value", "t": tick}], "outcome": "ABORT"}
    before = [r for r in rows if r["t"] < tick]
    if not before:
        return {"errors": [{"kind": "abort_without_prefix", "t": tick}], "outcome": "ABORT"}
    report = _assess(before, case, prefix=True)
    report["outcome"] = "ABORT"
    errors = report["errors"]
    for row in rows:
        t = row["t"]
        expected_controls = ((1, 1, 0, 0) if t < tick else
                             (0, 1, 0, 0) if control == "reset" else
                             (1, 0, 0, 0) if control == "disable" else (1, 1, 1, 1))
        if tuple(row[k] for k in controls) != expected_controls:
            errors.append({"kind": "abort_control", "t": t})
        if t < tick:
            continue
        if control == "reset":
            if (row["out"], row["oe"], row["rx"], row["rx_valid"], row["state"]) != (0, 0, 0, 0, "RUN"):
                errors.append({"kind": "reset_effect", "t": t})
        elif control == "disable":
            if any(row[k] != before[-1][k] for k in ("out", "oe", "rx", "rx_valid", "state")):
                errors.append({"kind": "disable_freeze", "t": t})
        elif row["target_oe"]:
            errors.append({"kind": "loader_target_connected", "t": t})
    report["halt"] = None
    report["abort"] = {"control": control, "t": tick}
    return report
