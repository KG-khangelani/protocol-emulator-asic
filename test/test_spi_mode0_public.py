# SPDX-License-Identifier: Apache-2.0
"""Public-pin SPI seed: conditional success plus retained RX counterexamples.

No internal engine observation and no production RTL extension. A successful
falsification test does not qualify P-SPI-HOST-4MODE or the broad mode-0 seed.
"""

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

from test import (check_readback, edge, encode, initialise, load_program,
                  write_data_register, G2_CURRENT)
from tools.spi_mode0_oracle import (assemble, bits, coupled_program,
                                   expected_gpio, miso_level, schedule)


async def prepare(dut, tx, *, half_period=25, order=1, late=True):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    words = [encode(item) for item in coupled_program(
        half_period, msb_first=order, late=late)]
    assert len(words) == 8
    await load_program(dut, words)
    await check_readback(dut, words)
    await write_data_register(dut, 1, tx)
    dut.ui_in.value = 0
    dut.uio_in.value = 2  # Idle MISO=1, not a preloaded first data bit.
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    assert int(dut.uo_out.value) == 0x20
    assert int(dut.uio_oe.value) == 0


async def read_result(dut):
    before = (int(dut.uio_out.value), int(dut.uio_oe.value))
    dut.ui_in.value = 0x62
    await Timer(1, unit="ps")
    raw = int(dut.uo_out.value)
    dut.ui_in.value = 0x63
    await Timer(1, unit="ps")
    valid = int(dut.uo_out.value)
    dut.ui_in.value = 0
    await Timer(1, unit="ps")
    assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == before
    return raw, valid


async def transaction(dut, tx, rx, wanted_raw, *, half_period=25, order=1,
                      response=1, late=True, stop_edge=None):
    timing = schedule(half_period, late=late)
    end = timing["halt"] if stop_edge is None else stop_edge
    observed_tx, observed_rx = [], []
    last_rise = None
    line = lambda q: miso_level(q, rx, half_period=half_period,
                                response_quarters=response, msb_first=order)
    dut.rst_n.value = 1
    dut.ena.value = 1
    for n in range(1, end + 1):
        for q in (4 * n - 2, 4 * n - 1):
            dut.uio_in.value = line(q) << 1
            await Timer(5, unit="ns")
        dut.uio_in.value = line(4 * n) << 1
        await Timer(1, unit="ps")
        dut.clk.value = 1
        now = int(get_sim_time(unit="ps"))
        if last_rise is not None:
            assert now - last_rise == 20000, (n, now - last_rise)
        last_rise = now
        await Timer(999, unit="ps")
        gpio = int(dut.uio_out.value), int(dut.uio_oe.value)
        assert gpio == expected_gpio(n, tx, half_period=half_period,
                                     msb_first=order, late=late), (n, gpio)
        assert gpio[1] & 2 == 0, "host drove target-owned MISO"
        status = int(dut.uo_out.value)
        if n < timing["halt"]:
            assert status >> 6 < 2, ("premature terminal", n, status)
        else:
            assert status == 0xA7, (n, status)
        if n in timing["rising"]:
            observed_tx.append(gpio[0] & 1)
            observed_rx.append(line(4 * n))
        spent = 0
        if n in (timing["raw_capture"] - 1, timing["raw_capture"],
                 timing["rising"][-1], timing["halt"]):
            actual = await read_result(dut)
            wanted = (wanted_raw, 1) if n >= timing["raw_capture"] else (0, 0)
            assert actual == wanted, (n, actual, wanted)
            spent = 3
        await Timer(4000 - spent, unit="ps")
        dut.uio_in.value = line(4 * n + 1) << 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
    if stop_edge is None:
        assert observed_tx == bits(tx, order)
        assert assemble(observed_rx, order) == rx
        assert await read_result(dut) == (wanted_raw, 1)
        dut._log.info("SPI seed order=%d response_q=%d late=%s target=%02x raw=%02x HALT=%d",
                      order, response, late, rx, wanted_raw, end)


@cocotb.test()
async def spi_mode0_public_conditional_and_counterexample(dut):
    # The last case illustrates why all-ones alone masks the coupling defect.
    cases = [(0x96, 0x69, 1, 1, True, 0x69),
             (0x96, 0x69, 1, 88, True, 0x69),
             (0x96, 0x69, 1, 89, True, 0xB4),
             (0x96, 0x69, 1, 96, True, 0xB4),
             (0x96, 0x69, 0, 1, True, 0x69),
             (0x96, 0x69, 0, 89, True, 0xD3),
             (0x96, 0x69, 1, 1, False, 0xB4),
             (0, 0, 1, 1, True, 0),
             (0x55, 0xAA, 1, 1, True, 0xAA),
             (255, 255, 1, 96, True, 255)]
    for tx, rx, order, response, late, wanted in cases:
        await prepare(dut, tx, order=order, late=late)
        await transaction(dut, tx, rx, wanted, order=order, response=response, late=late)


@cocotb.test()
async def spi_mode0_abort_reload_and_capacity_boundary(dut):
    await prepare(dut, 0x96)
    await transaction(dut, 0x96, 0x69, 0x69, stop_edge=127)
    before = (int(dut.uio_out.value), int(dut.uio_oe.value), int(dut.uo_out.value))
    assert before[0] & 4  # Disabled SCK high invalidates fixed-rate acceptance.
    for _ in range(5):
        await edge(dut, ena=0)
        assert (int(dut.uio_out.value), int(dut.uio_oe.value), int(dut.uo_out.value)) == before
    assert await read_result(dut) == (0, 0)
    await edge(dut, rst_n=0, ena=0)
    assert (int(dut.uio_out.value), int(dut.uio_oe.value), int(dut.uo_out.value)) == (0, 0, 0)
    await prepare(dut, 0x69)
    await transaction(dut, 0x69, 0x96, 0x96)
    # Keep the original capacity rejection on the original eight-word profile.
    # The current profile rejects 129 against its actual 128-word store.
    dut.uio_in.value = 0  # Target detached before loader ownership.
    await write_data_register(dut, 0, 129 if G2_CURRENT else 10)
    dut.ui_in.value = 0xA0
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == 0
    dut.ui_in.value = 0
    dut.uio_in.value = 2
    await edge(dut, ena=0)
    assert int(dut.uo_out.value) & 0x20 == 0
