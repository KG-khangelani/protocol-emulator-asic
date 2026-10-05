# SPDX-License-Identifier: Apache-2.0
"""Public-pin RX checks against frame mathematics, not Machine.edge."""

import cocotb
from cocotb.triggers import Timer

from test import (check_readback, edge, encode, initialise, load_program,
                  write_data_register)
from tools.uart_rx_oracle import Frame, expected_schedule, line_level, rx_program


async def runtime_snapshot(dut, addresses=(2, 3), *, held_address=4):
    """No clock/loader entry; caller budgets these 1ps settles into its clock."""
    before = (int(dut.uio_out.value), int(dut.uio_oe.value))
    values = []
    for address in addresses:
        dut.ui_in.value = 0x60 | address
        await Timer(1, unit="ps")
        values.append(int(dut.uo_out.value))
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == before
    dut.ui_in.value = 0
    await Timer(1, unit="ps")
    status = int(dut.uo_out.value)
    dut.ui_in.value = 0x60 | held_address
    await Timer(1, unit="ps")
    assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == before
    return status, values, len(addresses) + 2


async def prepare_rx(dut, period):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    words = [encode(instruction) for instruction in rx_program(period)]
    await load_program(dut, words)
    await check_readback(dut, words)
    await write_data_register(dut, 1, 0xFF)
    await write_data_register(dut, 4, 0xFF)
    dut.ui_in.value = 0x64  # Writable address + ui6 high across every RX edge.
    dut.uio_in.value = 2
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    status, values, _ = await runtime_snapshot(dut, (0, 1, 2, 3, 4, 31))
    assert (status, values) == (0x20, [0, 255, 0, 0, 255, 0])
    assert int(dut.uio_oe.value) == 0


async def drive_rx(dut, frames, *, period=434, start_quarter=17,
                   end_edge=None, terminal=0xA7, waveform=None,
                   normal_prefix=True, log=False):
    """20ns clocks; quarter-phase changes and read delays do not stretch them.

    The rising clock is 1ps after quarter tick 4*n, giving coincident raw
    transitions deterministic before-edge ordering. Each cycle is exactly
    20,000ps, including the optional runtime readback settling intervals.
    """
    schedule = expected_schedule(start_quarter=start_quarter, period=period)
    end_edge = schedule["halt"] if end_edge is None else end_edge
    waveform = waveform or (lambda q: line_level(
        q, frames, start_quarter=start_quarter, period=period))
    captures = dict(zip(schedule["raw_capture"], [f.payload for f in frames]))
    landmarks = {1: 0x21, 2: 0x61}
    if normal_prefix:
        for index in range(len(frames)):
            landmarks[schedule["detected_start"][index]] = 0x22
            landmarks[schedule["checked_start"][index]] = 0x24
            landmarks[schedule["first_data"][index]] = 0x65
            landmarks[schedule["raw_capture"][index]] = 0x65
            landmarks[schedule["checked_stop"][index]] = 0x21 if index == 0 else 0x27
    landmarks[end_edge] = terminal
    raw, valid = 0, 0
    first_data = schedule["first_data"][0] if normal_prefix else end_edge + 1
    dut.rst_n.value = 1
    dut.ena.value = 1
    for n in range(1, end_edge + 1):
        for quarter in (4 * n - 2, 4 * n - 1):
            dut.uio_in.value = waveform(quarter) << 1
            await Timer(5, unit="ns")
        dut.uio_in.value = waveform(4 * n) << 1
        await Timer(1, unit="ps")
        dut.clk.value = 1
        await Timer(999, unit="ps")
        if n in captures:
            raw, valid = captures[n], 1
        active = int(n >= first_data)
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (active, active), n
        assert int(dut.uo_out.value) == 255  # Held runtime TX-alt read survives.
        inspect_raw = n in captures or n + 1 in captures or n == end_edge
        status, values, spent_ps = await runtime_snapshot(dut, (2, 3) if inspect_raw else ())
        if inspect_raw:
            assert values == [raw, valid], (n, values, raw, valid)
        if n in landmarks:
            assert status == landmarks[n], (n, hex(status), hex(landmarks[n]))
            if log:
                dut._log.info("RX edge=%d status=%02x raw=%02x valid=%d", n, status, raw, valid)
        if n < end_edge:
            assert status >> 6 < 2, ("premature terminal", n, hex(status))
        await Timer(4000 - spent_ps, unit="ps")
        dut.uio_in.value = waveform(4 * n + 1) << 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
    status, values, _ = await runtime_snapshot(dut, (1, 2, 3, 4))
    assert (status, values) == (terminal, [255, raw, valid, 255])
    return raw, valid


@cocotb.test()
async def uart_rx_public_bounded_last_byte_delivery(dut):
    # Alphabet once at the minimal legal period; exact-period phase corners.
    for payload in range(256):
        await prepare_rx(dut, 4)
        assert await drive_rx(dut, [Frame(payload), Frame(payload ^ 255)], period=4) == (payload ^ 255, 1)
    for first, second, phase in ((0, 255, 0), (255, 0, 1), (85, 170, 2), (170, 85, 3)):
        await prepare_rx(dut, 434)
        assert await drive_rx(dut, [Frame(first), Frame(second)], start_quarter=16 + phase, log=True) == (second, 1)
        # Terminal data is retained with either enable; GPIO RX stays released.
        for enabled in (0, 1, 0):
            await edge(dut, ena=enabled)
            status, values, _ = await runtime_snapshot(dut, (2, 3))
            assert (status, values) == (0xA7, [second, 1])
            assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (1, 1)
        # Exact decode: bits6/5 separately do not select data; reserved reads zero.
        for selector in (0, 0x20, 0x40, 0x5F):
            dut.ui_in.value = selector
            await Timer(1, unit="ps")
            assert int(dut.uo_out.value) == 0xA7
        status, values, _ = await runtime_snapshot(dut, (0, 5, 31))
        assert (status, values) == (0xA7, [0, 0, 0])


@cocotb.test()
async def uart_rx_public_framing_and_bounded_timeouts(dut):
    schedule = expected_schedule()
    for bad_frame in (0, 1):
        frames = [Frame(0x5A, int(bad_frame != 0)), Frame(0xA5, int(bad_frame != 1))]
        await prepare_rx(dut, 434)
        raw, valid = await drive_rx(dut, frames, end_edge=schedule["checked_stop"][bad_frame], terminal=0xE6, log=True)
        assert (raw, valid) == (frames[bad_frame].payload, 1)
        # Raw-valid survives a framing fault; terminal FAULT rejects the batch.
        await edge(dut, ena=0)
        status, values, _ = await runtime_snapshot(dut)
        assert (status, values) == (0xE6, [raw, 1])
    await prepare_rx(dut, 434)
    assert await drive_rx(dut, [], end_edge=870, terminal=0xE1, normal_prefix=False, log=True) == (0, 0)
    await prepare_rx(dut, 434)
    assert await drive_rx(dut, [Frame(0x5A)], end_edge=schedule["checked_stop"][0] + 1 + 868,
                          terminal=0xE1, log=True) == (0x5A, 1)
    # A short low pulse is high again at the first start-center sample.
    await prepare_rx(dut, 434)
    pulse = lambda q: int(not (17 <= q < 17 + 434))
    assert await drive_rx(dut, [], end_edge=schedule["checked_start"][0], terminal=0xE3,
                          waveform=pulse, normal_prefix=False, log=True) == (0, 0)


@cocotb.test()
async def uart_rx_public_disable_reset_abort_then_reload(dut):
    schedule = expected_schedule()
    await prepare_rx(dut, 434)
    # Abort while frame two is incomplete; first raw result already exists.
    assert await drive_rx(dut, [Frame(0x5A), Frame(0xA5)],
                          end_edge=schedule["first_data"][1] + 2 * 434,
                          terminal=0x65, log=True) == (0x5A, 1)
    for level in (0, 1, 0):
        dut.uio_in.value = level << 1
        await edge(dut, ena=0)
        status, values, _ = await runtime_snapshot(dut)
        assert (status, values) == (0x65, [0x5A, 1])
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (1, 1)
    # Caller rejects this interrupted batch; never resume it as accepted RX.
    await edge(dut, rst_n=0, ena=0)
    status, values, _ = await runtime_snapshot(dut, (1, 2, 3, 4))
    assert (status, values) == (0, [0, 0, 0, 0])
    assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (0, 0)
    await prepare_rx(dut, 4)
    assert await drive_rx(dut, [Frame(0x96), Frame(0x69)], period=4) == (0x69, 1)
