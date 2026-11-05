# SPDX-License-Identifier: Apache-2.0
"""Public-pin candidate checks; production tests are run unchanged separately."""

import os
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, write_data_register
from test_spi_mode0_public import read_result
from tools.m1_contract_model import Instruction
from tools.spi_mode0_oracle import assemble, bits, expected_gpio, miso_level, schedule
from experiments.spi_phase.phase_programs import compact_program, encode, plain_program

COMPACT = os.environ["PHASE_COMPARE_VARIANT"] == "compact"


async def select_bank(dut, bank):
    await write_data_register(dut, 5, bank)


async def load_and_check(dut, words):
    assert len(words) <= (8 if COMPACT else 10)
    bank = 0
    for index, word in enumerate(words):
        desired = index // 8
        if desired != bank:
            await select_bank(dut, desired)
            bank = desired
        for lane in range(4):
            dut.ui_in.value = 0xC0 | ((index % 8) * 4 + lane)
            dut.uio_in.value = (word >> (8 * lane)) & 255
            await edge(dut)
            assert int(dut.uio_oe.value) == 0
    await write_data_register(dut, 0, len(words))  # Commit also restores bank zero.
    bank = 0
    for index, word in enumerate(words):
        desired = index // 8
        if desired != bank:
            await select_bank(dut, desired)
            bank = desired
        for lane in range(4):
            dut.ui_in.value = 0x80 | ((index % 8) * 4 + lane)
            await Timer(1, unit="ns")
            assert int(dut.uio_oe.value) == 255
            assert int(dut.uio_out.value) == ((word >> (8 * lane)) & 255)
    await write_data_register(dut, 0, len(words))  # Recommit after banked readback.
    assert int(dut.uo_out.value) & 0x20


async def prepare(dut, program, tx, idle=1):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_and_check(dut, [encode(w, compact=COMPACT) for w in program])
    await write_data_register(dut, 1, tx)
    dut.ui_in.value = 0
    dut.uio_in.value = idle << 1
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    assert int(dut.uo_out.value) == 0x20


async def transfer(dut, tx, rx, *, order, response, half=25):
    program = (compact_program if COMPACT else plain_program)(half, msb_first=order)
    await prepare(dut, program, tx)
    timing = schedule(half)
    observed = []
    previous = None
    line = lambda q: miso_level(q, rx, half_period=half, response_quarters=response, msb_first=order)
    dut.ena.value = 1
    for n in range(1, timing["halt"] + 1):
        for q in (4 * n - 2, 4 * n - 1):
            dut.uio_in.value = line(q) << 1
            await Timer(5, unit="ns")
        dut.uio_in.value = line(4 * n) << 1
        await Timer(1, unit="ps")
        dut.clk.value = 1
        now = int(get_sim_time(unit="ps"))
        if previous is not None:
            assert now - previous == 20000
        previous = now
        await Timer(999, unit="ps")
        value, oe = expected_gpio(n, tx, half_period=half, late=False, msb_first=order)
        if COMPACT and n >= 2:
            index = min((n - 2) // (2 * half), 7)
            value = (value & ~1) | bits(tx, order)[index]
            oe |= 1
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (value, oe), (n, value, oe)
        assert int(dut.uio_oe.value) & 2 == 0
        if n in timing["rising"]:
            observed.append(int(dut.uio_out.value) & 1)
            assert line(4 * n) == bits(rx, order)[len(observed) - 1]
        capture = timing["rising"][-1] + 2
        spent = 0
        if n in (capture - 1, capture, timing["halt"]):
            assert await read_result(dut) == ((rx, 1) if n >= capture else (0, 0)), n
            spent = 3
        status = int(dut.uo_out.value)
        if n == timing["halt"]:
            assert status == (0xA7 if COMPACT else 0xA9)
        else:
            assert status >> 6 < 2, (n, status)
        await Timer(4000 - spent, unit="ps")
        dut.uio_in.value = line(4 * n + 1) << 1
        await Timer(5, unit="ns")
        dut.clk.value = 0
    assert assemble(observed, order) == tx


@cocotb.test()
async def phase_public_all_bytes_and_response_corners(dut):
    for order in (0, 1):
        for rx in range(256):
            await transfer(dut, 255 - rx, rx, order=order, response=96)
        for response in (1, 88, 89):
            await transfer(dut, 0x96, 0x69, order=order, response=response)
    await transfer(dut, 0xA5, 0x69, order=1, response=12, half=4)
    dut._log.info("PHASE variant=%s: 519 public transfers PASS; exact clocks, both orders, late response, all bytes",
                  "compact" if COMPACT else "banked")


@cocotb.test()
async def phase_invalid_partial_and_loader_contract(dut):
    drive = Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1)
    sample = Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1)
    legacy = Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1, msb_first=1)
    cases = [([sample], 0), ([drive, drive], 1), ([drive, legacy], 1),
             ([legacy, drive], 1), ([drive, Instruction("HALT")], 1),
             ([drive, Instruction("SAMPLE", tx_pin=2, rx_pin=1, msb_first=1)], 1)]
    # Seventh completed phase sample followed by an invalid legacy eighth step.
    cases.append(([Instruction("LOOP", length=2, count=7), drive, sample,
                   drive, legacy, Instruction("HALT")], 4))
    for program, pc in cases:
        await prepare(dut, program, 0x96)
        for _ in range(24):
            await edge(dut)
            if int(dut.uo_out.value) >> 6 == 3:
                break
        assert int(dut.uo_out.value) == 0xE0 | pc
        assert await read_result(dut) == (0, 0)
        held = int(dut.uio_out.value), int(dut.uio_oe.value)
        await edge(dut)
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == held
    # Characterize the intentionally allocated versus still-reserved register.
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await write_data_register(dut, 5, 1)
    dut.ui_in.value = 0xA5
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == (0 if COMPACT else 1)
    await write_data_register(dut, 0, 9)
    dut.ui_in.value = 0
    await Timer(1, unit="ns")
    assert bool(int(dut.uo_out.value) & 0x20) is (not COMPACT)


@cocotb.test()
async def phase_pending_latched_freeze_reset_and_complete_legacy(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction_valid.value = 1
    dut.engine_tx_payload.value = 0x69
    dut.engine_tx_payload_alt.value = 0x96
    drive = encode(Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1))
    sample = encode(Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1))
    for _ in range(7):
        dut.engine_instruction.value = drive
        await edge(dut)
        dut.engine_instruction.value = sample
        await edge(dut)
    dut.engine_instruction.value = drive
    await edge(dut)
    pending = (encode(Instruction("SAMPLE", count=3, tx_pin=0, rx_pin=1, msb_first=1))
               if COMPACT else encode(Instruction("WAIT", count=3)))
    dut.engine_instruction.value = pending
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_wait_left.value)) == (1, 3)
    dut.engine_instruction.value = 0xFFFFFFFF  # No re-fetch while pending.
    dut.engine_instruction_valid.value = 0
    dut.engine_sampled_inputs.value = 2
    for _ in range(3):
        await edge(dut, ena=0)
        assert int(dut.engine_wait_left.value) == 3
        assert int(dut.engine_shift_result_write.value) == 0
    for _ in range(2):
        await edge(dut)
    await Timer(1, unit="ps")
    if COMPACT:
        assert (int(dut.engine_shift_result_write.value), int(dut.engine_shift_result_data.value)) == (1, 1)
        await edge(dut)
    else:
        assert int(dut.engine_shift_result_write.value) == 0
        await edge(dut)  # Ordinary WAIT retires without consuming RX.
        dut.engine_instruction_valid.value = 1
        dut.engine_instruction.value = sample
        await Timer(1, unit="ps")
        assert (int(dut.engine_shift_result_write.value), int(dut.engine_shift_result_data.value)) == (1, 1)
        await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_shift_active_status.value)) == (0, 0)
    assert int(dut.engine_shift_tx_slot_status.value) == 0
    # Full phase completion must leave both old UART payload slots usable.
    await edge(dut, rst_n=0, ena=0)  # Separate direct-port fixture: avoid PC overflow.
    dut.engine_instruction_valid.value = 1
    burst = encode(Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1, msb_first=1, burst=1, period=2))
    for payload in (0x69,):
        dut.engine_instruction.value = burst
        for tick in range(16):
            await edge(dut)
            assert int(dut.engine_gpio_value.value) & 1 == bits(payload, 1)[tick // 2]
        assert int(dut.engine_state.value) == 0
    assert int(dut.engine_shift_tx_slot_status.value) == 1
    for _ in range(8):
        dut.engine_instruction.value = drive
        await edge(dut)
        dut.engine_instruction.value = sample
        await edge(dut)
        assert int(dut.engine_shift_tx_slot_status.value) == 1
    dut.engine_instruction.value = burst
    for tick in range(16):
        await edge(dut)
        assert int(dut.engine_gpio_value.value) & 1 == bits(0x96, 1)[tick // 2]
    assert int(dut.engine_shift_tx_slot_status.value) == 0
    dut.engine_instruction.value = drive
    await edge(dut)
    dut.engine_instruction.value = pending
    await edge(dut)
    assert int(dut.engine_state.value) == 1
    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction.value = sample
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_gpio_oe.value)) == (3, 0)


@cocotb.test()
async def phase_aux_reserved_and_banked_nonalias(dut):
    drive = encode(Instruction("DRIVE", tx_pin=0, rx_pin=1, msb_first=1))
    sample = encode(Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1))
    for malformed in (drive | 1, sample | 1, drive | (1 << 20),
                      drive | (1 << 11), drive | (2 << 11)):
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_and_check(dut, [malformed])
        dut.ui_in.value = 0
        await edge(dut)
        assert int(dut.uo_out.value) == 0xE0
        assert int(dut.uio_oe.value) == 0
        assert await read_result(dut) == (0, 0)
    if COMPACT:
        program = [Instruction("SET", mask=255, value=0xA0, oe=0xF0),
                   Instruction("DRIVE", mask=0x14, value=0xFF, tx_pin=0, rx_pin=1, msb_first=1),
                   Instruction("SAMPLE", tx_pin=0, rx_pin=1, msb_first=1)]
        await prepare(dut, program, 0)
        await edge(dut)
        await edge(dut)
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (0xB4, 0xF5)
        held = int(dut.uio_out.value), int(dut.uio_oe.value)
        await edge(dut)
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == held
        return
    # Every stored byte must survive writes outside the bank-one implemented window.
    words = [0x10203040 + i * 0x01010101 for i in range(10)]
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_and_check(dut, words)
    await select_bank(dut, 1)
    for address in range(8, 32):
        dut.ui_in.value = 0xC0 | address
        dut.uio_in.value = 0xFF
        await edge(dut)
        dut.ui_in.value = 0x80 | address
        await Timer(1, unit="ns")
        assert int(dut.uio_out.value) == 0
    for index, word in enumerate(words):
        await select_bank(dut, index // 8)
        for lane in range(4):
            dut.ui_in.value = 0x80 | ((index % 8) * 4 + lane)
            await Timer(1, unit="ns")
            assert int(dut.uio_out.value) == (word >> (8 * lane)) & 255
    await select_bank(dut, 1)
    dut.ui_in.value = 0xE5
    dut.uio_in.value = 0
    await edge(dut, ena=0)
    dut.ui_in.value = 0xA5
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == 1
    await select_bank(dut, 2)
    dut.ui_in.value = 0xA5
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == 0
    for length in (9, 10, 11, 0, 255):
        await write_data_register(dut, 0, length)
        dut.ui_in.value = 0
        await Timer(1, unit="ns")
        assert bool(int(dut.uo_out.value) & 0x20) == (length in (9, 10))
