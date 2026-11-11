"""External digital host reference; no production VM/RTL or Machine.edge."""

from .uart_rx_oracle import expected_schedule, rx_program


def visible_raw(edge, first, second, *, period=434, start_quarter=17):
    """Independent register lifetime oracle for a successfully framed batch."""
    c1, c2 = expected_schedule(period=period, start_quarter=start_quarter)["raw_capture"]
    return (0, 0) if edge < c1 else (first, 1) if edge < c2 else (second, 1)


class HostReader:
    """Reference synchronous host, not an OS/pad-latency implementation.

    Requests consume only scheduled public observations. The caller owns fresh
    image/valid-zero handoff, exact periods and control continuity; interrupt()
    is mandatory when that continuity fails. Nothing delivers before accepted.
    """

    def __init__(self, period=434, poll_gap=4338, read_latency=2, first_poll=1):
        if any(type(n) is not int for n in (period, poll_gap, read_latency, first_poll)):
            raise ValueError("host timing parameters must be integers")
        rx_program(period)
        if not (poll_gap >= 1 and read_latency >= 1 and
                poll_gap + read_latency <= 10 * period and 1 <= first_poll <= poll_gap):
            raise ValueError("require H>=1,L>=1,H+L<=10P and first_poll in 1..H")
        self.period = period
        self.gap = poll_gap
        self.latency = read_latency
        self.next_poll = first_poll
        self.pending = None
        self.first = None
        self.accepted = None
        self.rejected = None
        self.events = []
        self.last_edge = 0

    def interrupt(self, reason="control interruption"):
        if self.accepted is not None:
            return  # Already delivered; permitted terminal disable cannot revoke it.
        self.first = None
        self.pending = None
        self.accepted = None
        self.rejected = reason

    def requests(self, edge):
        if edge != self.last_edge + 1:
            self.interrupt("host clock/service gap")
        self.last_edge = edge
        if self.accepted is not None or self.rejected:
            return ()
        return tuple(kind for kind, due in (
            ("poll", self.next_poll),
            (self.pending[0], self.pending[1]) if self.pending else ("none", -1))
            if edge == due)

    def observe(self, edge, requests, status, valid, data=None):
        if not requests or self.rejected or self.accepted is not None:
            return
        if not status & 0x20 or status >> 6 == 3:
            self.interrupt("not-ready/fault")
            return
        if "poll" in requests:
            self.next_poll += self.gap
            if status >> 6 == 2:
                if status != 0xA7 or not valid or self.first is None:
                    self.interrupt("HALT without first cache/valid image")
                    return
                if self.pending is None:
                    self.pending = ("second", edge + self.latency)
            elif valid and self.first is None and self.pending is None:
                self.pending = ("first", edge + self.latency)
        if "first" in requests:
            if not valid:
                self.interrupt("first copy invalid")
                return
            self.first = data
            self.pending = None
            self.events.append((edge, "tentative", data))
        if "second" in requests:
            if status != 0xA7 or not valid or self.first is None:
                self.interrupt("terminal copy invalid")
                return
            self.accepted = (self.first, data)
            self.pending = None
            self.events.append((edge, "accepted", self.accepted))
