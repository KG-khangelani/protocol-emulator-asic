# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0
# Modified 2026-09-22: independent M0 pin-level cycle oracle.
import random
import cocotb
from cocotb.triggers import Timer

SEED = 20260922

def observe(dut, expected):
    assert int(dut.uo_out.value) == expected, f"expected {expected:#04x}, got {dut.uo_out.value}"
    assert int(dut.uio_oe.value) == 0, "bidirectional pins must remain inputs"
    assert int(dut.uio_out.value) == 0, "unused output path must be defined"

def initialise(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0

async def cycle(dut, expected, reset_n=1, enable=1, noise=None):
    # Inputs change while clock is low; observe one ns after the active edge.
    dut.rst_n.value = reset_n
    dut.ena.value = enable
    await Timer(10, unit="ns")
    dut.clk.value = 1
    await Timer(1, unit="ns")
    observe(dut, expected)
    if noise:
        dut.ui_in.value = noise.randrange(256)
        dut.uio_in.value = noise.randrange(256)
        dut.ena.value = 1 - enable
        dut.rst_n.value = 1 - reset_n
    await Timer(9, unit="ns")
    observe(dut, expected)  # no state transition between active edges
    dut.clk.value = 0

@cocotb.test()
async def reset_wrap_hold_and_resume(dut):
    initialise(dut)
    await cycle(dut, 0, reset_n=0, enable=0)
    for n in range(1, 513):
        await cycle(dut, n % 256)
    for _ in range(17):
        await cycle(dut, 0, enable=0)
    await cycle(dut, 1)
    await cycle(dut, 2)
    # Reset must win even when disabled and when state is nonzero.
    await cycle(dut, 0, reset_n=0, enable=0)
    await cycle(dut, 1)
    await cycle(dut, 0, reset_n=0, enable=1)
    await cycle(dut, 1)

@cocotb.test()
async def seeded_control_and_input_noise(dut):
    initialise(dut)
    rng = random.Random(SEED)
    dut._log.info("seed=%d", SEED)
    await cycle(dut, 0, reset_n=0, enable=0)
    # Oracle counts accepted edges since the latest sampled reset.
    accepted_edges = 0
    for _ in range(1024):
        reset_n = int(rng.randrange(13) != 0)
        enable = rng.randrange(2)
        if not reset_n:
            accepted_edges = 0
        elif enable:
            accepted_edges += 1
        await cycle(dut, accepted_edges % 256, reset_n, enable, rng)
