# SPDX-License-Identifier: Apache-2.0
"""Public-pin transport with an independently scheduled target and native clock.

No executor/model imports or hierarchical DUT handles. Clock transitions run
in the simulator; Python wakes on public changes or declared target events.
Target callbacks must use public pin events and schedule strictly future drives.
"""
import heapq
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import First, Timer, ValueChange
from cocotb.utils import get_sim_time


async def public_snapshot(dut, *, extended_pc=False):
    status = int(dut.uo_out.value)
    row = {"out": int(dut.uio_out.value), "oe": int(dut.uio_oe.value),
           "state": ("RUN", "WAIT", "HALT", "FAULT")[status >> 6], "pc": status & 31}
    dut.ui_in.value = 0x62
    await Timer(1, unit="ps")
    row["rx"] = int(dut.uo_out.value)
    dut.ui_in.value = 0x63
    await Timer(1, unit="ps")
    row["rx_valid"] = int(dut.uo_out.value)
    if extended_pc:
        dut.ui_in.value = 0x66
        await Timer(1, unit="ps")
        row["pc"] = int(dut.uo_out.value)
    dut.ui_in.value = 0
    await Timer(1, unit="ps")
    return row


async def run_bus(dut, target, *, bound_ticks, terminal_hold=800, extended_pc=False):
    """Run from ena=0/clk=0 after public loading and two input flush edges.

    A tick is 5 ns; timestamps denote the post-edge grid interval. Runtime
    selectors settle within four picoseconds, before any next 5 ns grid event.
    A target drive is a (future tick, bit mask, pull-low value) triple.
    """
    rows = []
    queue = []
    target_oe = 0
    terminal = None
    dut.ui_in.value = 0
    await Timer(1, unit="ps")
    current = await public_snapshot(dut, extended_pc=extended_pc)
    bus = 3 & ~current["oe"]
    dut.uio_in.value = bus
    rows.append(dict(current, t=0, target_out=0, target_oe=0, bus=bus))
    dut.ena.value = 1
    await Timer(1, unit="ps")
    # Clock's first posedge is 10 ns from start; define it as core edge one.
    origin = int(get_sim_time(unit="ps")) - 10000
    clock = Clock(dut.clk, 20, unit="ns", impl="gpi")
    clock.start(start_high=False)

    def schedule(events, tick):
        for when, mask, value in events:
            assert type(when) is int and when > tick, (when, tick)
            assert 0 <= mask <= 3 and value & ~mask == 0
            heapq.heappush(queue, (when, mask, value))

    try:
        while True:
            now = int(get_sim_time(unit="ps"))
            stop_tick = terminal+terminal_hold if terminal is not None else bound_ticks
            next_tick = min(queue[0][0], stop_tick) if queue else stop_tick
            delay = origin+5000*next_tick-now
            assert delay > 0, (next_tick, now, origin)
            await First(ValueChange(dut.uio_out), ValueChange(dut.uio_oe),
                        ValueChange(dut.uo_out), Timer(delay, unit="ps"))
            await Timer(1, unit="ps")
            tick = (int(get_sim_time(unit="ps"))-origin)//5000
            previous = current
            current = await public_snapshot(dut, extended_pc=extended_pc)
            schedule(target.controller(tick, previous, current), tick)
            while queue and queue[0][0] <= tick:
                _, mask, value = heapq.heappop(queue)
                target_oe = (target_oe & ~mask) | value
            # Real digital resolution even for the deliberately active-high
            # controller control; the acceptance checker separately rejects it.
            resolved = ((current["out"] & current["oe"]) | ~current["oe"]) & ~target_oe & 3
            dut.uio_in.value = resolved
            schedule(target.bus(tick, bus, resolved), tick)
            bus = resolved
            row = dict(current, t=tick, target_out=0, target_oe=target_oe, bus=bus)
            if rows[-1]["t"] == tick:
                rows[-1] = row
            elif any(row[k] != rows[-1][k] for k in row if k != "t"):
                rows.append(row)
            if current["state"] in ("HALT", "FAULT") and terminal is None:
                terminal = tick
            if tick >= stop_tick:
                if rows[-1]["t"] != tick:
                    rows.append(row)
                break
    finally:
        clock.stop()
        dut.clk.value = 0
        dut.ena.value = 0
        await Timer(1, unit="ps")
    return rows
