# SPDX-License-Identifier: Apache-2.0
"""Procedural I2C fixture writer, independent of the acceptance implementation.

This is a waveform reference, not an executor or a public-loaded RTL result.
Constants and byte loops are intentionally separate from the oracle. Boundary
tests include hand-calculated edge tables so shared assumptions are observable.
"""


def waveform(case, *, stretches=None, response=4, low=1040, high=960,
             first_idle=940, start_hold=800, restart_setup=940,
             stop_setup=800, bus_free=940):
    """stretches maps one-based SCL releases to extra raw-low ticks or None.

    response is target SDA latency after falling SCL (5 ns ticks). Stretches
    affect SCL only; the fixture must match the separately declared outcome.
    None means permanently held low. A finite late release triggers cleanup.
    """
    stretches = stretches or {}
    rows = []
    state = {"t": 0, "out": 0, "oe": 28, "target_out": 0,
             "target_oe": 0, "bus": 3, "state": "RUN", "rx": 0, "rx_valid": 0}

    def emit(t, **change):
        if t < state["t"]:
            raise ValueError("fixture events out of order")
        state.update(change)
        state["t"] = t
        state["bus"] = (~(state["oe"] | state["target_oe"])) & 3
        if rows and rows[-1]["t"] == t:
            rows[-1] = dict(state)
        else:
            rows.append(dict(state))

    def controller(t, mask, pulled):
        emit(t, oe=(state["oe"] & ~mask) | (pulled & mask))

    def target(t, mask, pulled):
        emit(t, target_oe=(state["target_oe"] & ~mask) | (pulled & mask))

    def rounded(t):
        return ((t+3)//4)*4

    release_number = 0
    stopped_by_timeout = False

    def release_clock(at):
        nonlocal release_number, stopped_by_timeout
        release_number += 1
        controller(at, 1, 0)
        extra = stretches.get(release_number, 0)
        raw_high = None if extra is None else at+extra
        observed = None if raw_high is None else (raw_high//4+3)*4
        deadline = at+200000
        if raw_high is not None and raw_high <= deadline:
            target(raw_high, 1, 0)
        if observed is None or observed > deadline:
            emit(deadline+4, out=12, oe=28)
            emit(deadline+8, state="HALT")
            emit(deadline+64)
            stopped_by_timeout = True
            return None
        return rounded(raw_high)

    def prepare_clock_hold(at):
        # Target can assert SCL while the controller already holds it low.
        if stretches.get(release_number+1, 0) != 0:
            target(at, 1, 1)

    def bit(at, value, sender):
        """One low/high pulse; at is the previous falling SCL edge."""
        prepare_clock_hold(at+1)
        if sender == "controller":
            # Target releases during low before the next controller bit.
            target(at+2, 2, 0)
            controller(at+4, 2, 0 if value else 2)
        else:
            controller(at+4, 2, 0)
            target(at+max(4, response), 2, 0 if value else 2)
        rise = release_clock(at+low)
        if rise is None:
            return None
        fall = rise+high
        controller(fall, 1, 1)
        return fall

    def byte(at, value, sender):
        for shift in range(7, -1, -1):
            at = bit(at, (value >> shift) & 1, sender)
            if at is None:
                return None
        return at

    def send_and_ack(at, value, reject):
        at = byte(at, value, "controller")
        return None if at is None else bit(at, int(reject), "target")

    def finish(at, outcome):
        if at is None:
            return
        prepare_clock_hold(at+1)
        target(at+2, 2, 0)
        controller(at+4, 2, 2)
        rise = release_clock(at+low)
        if rise is None:
            return
        controller(rise+stop_setup, 2, 0)
        emit(rise+stop_setup+bus_free, out=4 if outcome == "OK" else 8)
        emit(rise+stop_setup+bus_free+4, state="HALT")
        emit(rise+stop_setup+bus_free+8)

    emit(0)
    controller(first_idle, 2, 2)
    t = first_idle+start_hold
    controller(t, 1, 1)
    t = send_and_ack(t, 2*case.address+int(case.kind == "read"), case.nack == "address")
    if t is None:
        return rows
    if case.nack == "address":
        finish(t, "NACK")
        return rows
    if case.kind != "read":
        t = send_and_ack(t, case.tx, case.nack == "data")
        if t is None:
            return rows
        if case.nack == "data" or case.kind == "write":
            finish(t, "NACK" if case.nack else "OK")
            return rows
        prepare_clock_hold(t+1)
        target(t+2, 2, 0)
        controller(t+4, 2, 0)
        rise = release_clock(t+low)
        if stopped_by_timeout:
            return rows
        controller(rise+restart_setup, 2, 2)
        t = rise+restart_setup+start_hold
        controller(t, 1, 1)
        t = send_and_ack(t, 2*case.address+1, case.nack == "read_address")
        if t is None:
            return rows
        if case.nack == "read_address":
            finish(t, "NACK")
            return rows
    t = byte(t, case.rx, "target")
    if t is None:
        return rows
    # The reference makes the publicly readable byte available after eight bits.
    capture_tick = t+4
    t = bit(t, 1, "controller")
    finish(t, "OK")
    for row in rows:
        if row["t"] >= capture_tick:
            row.update(rx=case.rx, rx_valid=1)
    return rows
