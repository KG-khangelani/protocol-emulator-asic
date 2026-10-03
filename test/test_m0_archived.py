"""Historical M0 waveform test, pinned to the archived qualified M0 RTL."""

import cocotb
from cocotb.triggers import Timer


def initialise(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0


async def cycle(dut, expected, reset_n=1, enable=1):
    dut.rst_n.value = reset_n
    dut.ena.value = enable
    await Timer(10, unit="ns")
    dut.clk.value = 1
    await Timer(1, unit="ns")
    assert int(dut.uo_out.value) == expected
    await Timer(9, unit="ns")
    dut.clk.value = 0


@cocotb.test()
async def archived_reset_wrap_hold_and_resume(dut):
    initialise(dut)
    await cycle(dut, 0, reset_n=0, enable=0)
    for n in range(1, 513):
        await cycle(dut, n % 256)
    for _ in range(17):
        await cycle(dut, 0, enable=0)
    await cycle(dut, 1)
    await cycle(dut, 2)
    await cycle(dut, 0, reset_n=0, enable=0)
    await cycle(dut, 1)
    await cycle(dut, 0, reset_n=0, enable=1)
    await cycle(dut, 1)
