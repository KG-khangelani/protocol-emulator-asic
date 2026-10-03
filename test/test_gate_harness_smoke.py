# SPDX-License-Identifier: Apache-2.0
"""Lightweight GL_TEST-shaped harness check using RTL, not a gate netlist."""

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def public_handles_reset_without_direct_engine(dut):
    assert not hasattr(dut, "engine_instruction")
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(10, unit="ns")
    dut.clk.value = 1
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == 0
    assert int(dut.uio_out.value) == 0
    assert int(dut.uio_oe.value) == 0
