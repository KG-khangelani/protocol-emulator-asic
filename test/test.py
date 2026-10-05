# SPDX-License-Identifier: Apache-2.0
"""Independent cycle checks for the M1 preloaded top and directly driven core."""

import os
import random
from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.m1_contract_model import Instruction, Machine, State

SEED = 20261002
STATE_BITS = {State.RUN: 0, State.WAIT: 1, State.HALT: 2, State.FAULT: 3}


def encode(instruction):
    if instruction.opcode == "SET":
        return (instruction.mask << 16) | (instruction.oe << 8) | instruction.value
    if instruction.opcode == "WAIT":
        return (1 << 30) | instruction.count
    if instruction.opcode == "LOOP":
        return (1 << 30) | (1 << 29) | (instruction.length << 24) | instruction.count
    if instruction.opcode == "HALT":
        return 2 << 30
    if instruction.opcode == "SHIFT_STEP":
        return ((2 << 30) | (1 << 29) | (instruction.msb_first << 28) |
                (instruction.tx_pin << 25) | (instruction.rx_pin << 22))
    if instruction.opcode == "WAIT_PIN":
        return ((3 << 30) | (instruction.pin << 27) | (instruction.level << 26) |
                (instruction.timeout_skip << 25) | instruction.count)
    return 3 << 30


def initialise(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    if hasattr(dut, "engine_instruction"):
        dut.engine_instruction.value = 0
        dut.engine_instruction_valid.value = 0
        dut.engine_sampled_inputs.value = 0
        dut.engine_tx_payload.value = 0


async def edge(dut, *, rst_n=1, ena=1):
    dut.rst_n.value = rst_n
    dut.ena.value = ena
    await Timer(10, unit="ns")
    dut.clk.value = 1
    await Timer(1, unit="ns")
    await Timer(9, unit="ns")
    dut.clk.value = 0


async def load_program(dut, words):
    for word_index, word in enumerate(words):
        for lane in range(4):
            dut.ui_in.value = 0xC0 | (word_index * 4 + lane)
            dut.uio_in.value = (word >> (8 * lane)) & 0xFF
            await edge(dut)
            assert int(dut.uio_oe.value) == 0
    dut.ui_in.value = 0xE0
    dut.uio_in.value = len(words)
    await edge(dut)
    assert int(dut.uo_out.value) & 0x20


async def check_readback(dut, words):
    for word_index, word in enumerate(words):
        for lane in range(4):
            dut.ui_in.value = 0x80 | (word_index * 4 + lane)
            await Timer(1, unit="ns")
            assert int(dut.uio_oe.value) == 0xFF
            assert int(dut.uio_out.value) == ((word >> (8 * lane)) & 0xFF)
    dut.ui_in.value = 0xA0
    await Timer(1, unit="ns")
    assert int(dut.uio_out.value) == len(words)


async def write_data_register(dut, address, value):
    dut.ui_in.value = 0xE0 | address
    dut.uio_in.value = value
    await edge(dut)
    assert int(dut.uio_oe.value) == 0


async def read_data_register(dut, address):
    dut.ui_in.value = 0xA0 | address
    await Timer(1, unit="ns")
    assert int(dut.uio_oe.value) == 0xFF
    return int(dut.uio_out.value)


def observe_engine(dut, expected):
    actual = (
        int(dut.engine_pc.value), int(dut.engine_state.value),
        int(dut.engine_wait_left.value), int(dut.engine_gpio_value.value),
        int(dut.engine_gpio_oe.value), int(dut.engine_shift_active_status.value),
        int(dut.engine_shift_bits_done_status.value),
        int(dut.engine_shift_result_write.value),
        int(dut.engine_shift_result_data.value),
    )
    wanted = (
        expected.pc, STATE_BITS[expected.state], expected.wait_left,
        expected.gpio_value, expected.gpio_oe, int(expected.shift_active),
        expected.shift_bits_done, int(expected.shift_result_write),
        expected.shift_result_data,
    )
    assert actual == wanted, f"RTL {actual} != semantic model {wanted}"


def observe_shift_engine(dut, expected):
    actual = (
        int(dut.engine_pc.value), int(dut.engine_state.value),
        int(dut.engine_wait_left.value), int(dut.engine_gpio_value.value),
        int(dut.engine_gpio_oe.value), int(dut.engine_loop_active_status.value),
        int(dut.engine_loop_remaining_status.value),
        int(dut.engine_loop_start_status.value), int(dut.engine_loop_end_status.value),
        int(dut.engine_shift_active_status.value),
        int(dut.engine_shift_bits_done_status.value),
        int(dut.engine_shift_msb_first_status.value),
        int(dut.engine_shift_tx_pin_status.value),
        int(dut.engine_shift_rx_pin_status.value),
        int(dut.engine_shift_tx_data_status.value),
        int(dut.engine_shift_rx_data_status.value),
    )
    wanted = (
        expected.pc, STATE_BITS[expected.state], expected.wait_left,
        expected.gpio_value, expected.gpio_oe, int(expected.loop_active),
        expected.loop_remaining, expected.loop_start, expected.loop_end,
        int(expected.shift_active), expected.shift_bits_done,
        int(expected.shift_msb_first), expected.shift_tx_pin,
        expected.shift_rx_pin, expected.shift_tx_data, expected.shift_rx_data,
    )
    assert actual == wanted, f"shift RTL {actual} != semantic model {wanted}"


@cocotb.test()
async def public_pin_reload_changes_observable_program(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    program_a = [encode(Instruction("SET", mask=0xFF, value=0xA5, oe=0xFF)), encode(Instruction("HALT"))]
    await load_program(dut, program_a)
    await check_readback(dut, program_a)
    dut.ui_in.value = 0
    await edge(dut)
    assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == (0x21, 0xA5, 0xFF)
    await edge(dut)
    assert int(dut.uo_out.value) == 0xA1

    await edge(dut, rst_n=0, ena=0)
    assert int(dut.uo_out.value) == 0
    program_b = [
        encode(Instruction("SET", mask=0xFF, value=0x3C, oe=0xFF)),
        encode(Instruction("WAIT", count=1)),
        encode(Instruction("SET", mask=0x0F, value=0x05, oe=0x09)),
        encode(Instruction("HALT")),
    ]
    await load_program(dut, program_b)
    await check_readback(dut, program_b)
    dut.ui_in.value = 0
    expected = [
        (0x21, 0x3C, 0xFF), (0x61, 0x3C, 0xFF),
        (0x22, 0x3C, 0xFF), (0x23, 0x35, 0xF9), (0xA3, 0x35, 0xF9),
    ]
    for status, value, oe in expected:
        await edge(dut)
        assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == (status, value, oe)


@cocotb.test()
async def invalid_length_never_releases_engine(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    dut.ui_in.value = 0xE0
    dut.uio_in.value = 9
    await edge(dut)
    assert int(dut.uo_out.value) == 0
    dut.ui_in.value = 0
    for _ in range(3):
        await edge(dut)
        assert int(dut.uo_out.value) == 0
        assert int(dut.uio_oe.value) == 0


@cocotb.test()
async def synchronized_input_wait_event_and_timeout(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    event_program = [
        encode(Instruction("WAIT_PIN", pin=2, level=1, count=4)),
        encode(Instruction("SET", mask=1, value=1, oe=1)),
        encode(Instruction("HALT")),
    ]
    await load_program(dut, event_program)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await edge(dut, ena=0)
    await edge(dut, ena=0)  # flush loader traffic from the two-stage sampler
    await edge(dut)
    assert int(dut.uo_out.value) == 0x60  # waiting at pc0, ready
    dut.uio_in.value = 0x04
    await edge(dut)
    assert int(dut.uo_out.value) == 0x60
    await edge(dut)
    assert int(dut.uo_out.value) == 0x60
    await edge(dut)
    assert int(dut.uo_out.value) == 0x21  # synchronized match advances
    await edge(dut)
    assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (1, 1)

    await edge(dut, rst_n=0, ena=0)
    timeout_program = [encode(Instruction("WAIT_PIN", pin=3, level=1, count=2))]
    await load_program(dut, timeout_program)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await edge(dut, ena=0)
    await edge(dut, ena=0)
    await edge(dut)
    assert int(dut.uo_out.value) == 0x60
    await edge(dut, ena=0)
    assert int(dut.uo_out.value) == 0x60  # disabled edge does not consume timeout
    await edge(dut)
    assert int(dut.uo_out.value) == 0x60
    await edge(dut)
    assert int(dut.uo_out.value) == 0xE0  # timeout enters FAULT at pc0


@cocotb.test()
async def k_input_wait_public_program_event_timeout_and_reload(dut):
    """Independent public-pin trace for the adopted K-INPUT-WAIT kernel."""
    program = [
        encode(Instruction("WAIT_PIN", pin=2, level=1, count=4, timeout_skip=1)),
        encode(Instruction("SET", mask=1, value=1, oe=1)),
        encode(Instruction("HALT")),
    ]

    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_program(dut, program)
    await check_readback(dut, program)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await edge(dut, ena=0)
    await edge(dut, ena=0)

    await edge(dut)  # execute WAIT_PIN
    assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == (0x60, 0, 0)
    dut.uio_in.value = 0x04
    event_status = [0x60, 0x60, 0x21, 0x22, 0xA2]
    event_gpio = [(0, 0), (0, 0), (0, 0), (1, 1), (1, 1)]
    for expected_status, expected_gpio in zip(event_status, event_gpio):
        await edge(dut)
        assert int(dut.uo_out.value) == expected_status
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == expected_gpio

    await edge(dut, rst_n=0, ena=0)
    assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == (0, 0, 0)
    await load_program(dut, program)
    await check_readback(dut, program)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await edge(dut, ena=0)
    await edge(dut, ena=0)

    timeout_status = [0x60, 0x60, 0x60, 0x60, 0x22, 0xA2]
    for expected_status in timeout_status:
        await edge(dut)
        assert int(dut.uo_out.value) == expected_status
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (0, 0)


@cocotb.test()
async def k_bounded_loop_public_program_counts(dut):
    """Independent public trace for counts 0, 1, 2 and maximum 255."""
    for count in (0, 1, 2, 255):
        program = [
            encode(Instruction("LOOP", length=2, count=count)),
            encode(Instruction("SET", mask=1, value=1, oe=1)),
            encode(Instruction("SET", mask=1, value=0, oe=1)),
            encode(Instruction("HALT")),
        ]
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_program(dut, program)
        await check_readback(dut, program)
        dut.ui_in.value = 0
        dut.uio_in.value = 0

        await edge(dut)  # LOOP: skip or enter body
        assert int(dut.uo_out.value) == (0x23 if count == 0 else 0x21)
        if count == 2:
            held = (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value))
            await edge(dut, ena=0)
            assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == held

        for iteration in range(count):
            await edge(dut)
            assert int(dut.uio_out.value) == 1
            assert int(dut.uio_oe.value) == 1
            assert int(dut.uo_out.value) == 0x22
            await edge(dut)
            assert int(dut.uio_out.value) == 0
            assert int(dut.uio_oe.value) == 1
            assert int(dut.uo_out.value) == (0x23 if iteration + 1 == count else 0x21)

        await edge(dut)
        assert int(dut.uo_out.value) == 0xA3
        assert (int(dut.uio_out.value), int(dut.uio_oe.value)) == (0, 0 if count == 0 else 1)


@cocotb.test()
async def loop_target_overflow_faults_without_alias(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    program = [encode(Instruction("LOOP", length=31, count=0))]
    assert program == [0x7F000000]
    await load_program(dut, program)
    await check_readback(dut, program)
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await edge(dut)
    assert int(dut.uo_out.value) == 0xE0  # FAULT at PC0, never wrapped RUN


@cocotb.test()
async def k_shift_8_public_payload_both_orders(dut):
    """Independent public-pin K-SHIFT-8 traces with synchronized RX data."""
    cases = ((0, 0x96, 0x3A), (1, 0x69, 0xC5))
    for msb_first, payload, received in cases:
        program = [
            encode(Instruction("LOOP", length=1, count=8)),
            encode(Instruction("SHIFT_STEP", msb_first=msb_first, tx_pin=0, rx_pin=1)),
            encode(Instruction("HALT")),
        ]
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_program(dut, program)
        await check_readback(dut, program)
        await write_data_register(dut, 1, payload)
        assert await read_data_register(dut, 1) == payload
        assert await read_data_register(dut, 3) == 0

        indices = list(range(7, -1, -1) if msb_first else range(8))
        rx_bits = [(received >> index) & 1 for index in indices]
        tx_bits = [(payload >> index) & 1 for index in indices]
        dut.ui_in.value = 0
        dut.uio_in.value = rx_bits[0] << 1
        await edge(dut, ena=0)
        await edge(dut, ena=0)
        held = (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value))
        await edge(dut, ena=0)
        assert (int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)) == held

        dut.uio_in.value = rx_bits[1] << 1
        await edge(dut)  # LOOP enters the one-word body.
        assert int(dut.uo_out.value) == 0x21
        for bit_index, expected_tx in enumerate(tx_bits):
            if bit_index + 2 < 8:
                dut.uio_in.value = rx_bits[bit_index + 2] << 1
            await edge(dut)
            assert (int(dut.uio_out.value) & 1) == expected_tx
            assert (int(dut.uio_oe.value) & 0x03) == 0x01
            assert int(dut.uo_out.value) == (0x22 if bit_index == 7 else 0x21)

        # Observe result/valid combinationally before another rising edge. This
        # rejects an implementation that defers integrated store capture to HALT.
        assert await read_data_register(dut, 2) == received
        assert await read_data_register(dut, 3) == 1
        dut.ui_in.value = 0
        await edge(dut)  # HALT follows the same-edge eighth-step result capture.
        assert int(dut.uo_out.value) == 0xA2
        assert await read_data_register(dut, 2) == received
        assert await read_data_register(dut, 3) == 1
        await write_data_register(dut, 4, 0x5A)
        assert await read_data_register(dut, 4) == 0
        assert await read_data_register(dut, 1) == payload
        assert await read_data_register(dut, 2) == received
        assert await read_data_register(dut, 3) == 1
        await write_data_register(dut, 2, received ^ 0xFF)
        assert await read_data_register(dut, 2) == received
        assert await read_data_register(dut, 3) == 1
        await write_data_register(dut, 1, payload ^ 0xFF)
        assert await read_data_register(dut, 1) == (payload ^ 0xFF)
        assert await read_data_register(dut, 2) == received
        assert await read_data_register(dut, 3) == 0


@cocotb.test(skip=os.getenv("GATES") == "yes")
async def shift_trace_matches_semantic_model(dut):
    cases = (
        (0, 0x96, 0x3A, False),
        (1, 0x69, 0xC5, False),
        (0, 0x00, 0xFF, False),
        (1, 0xFF, 0x00, False),
        (0, 0xA5, 0xFF, True),
    )
    for msb_first, payload, received, interleaved in cases:
        body = [Instruction("SHIFT_STEP", msb_first=msb_first, tx_pin=0, rx_pin=1)]
        if interleaved:
            body.extend((Instruction("SET", mask=4, value=4, oe=4),
                         Instruction("WAIT", count=0)))
        program = [Instruction("LOOP", length=len(body), count=8), *body,
                   Instruction("HALT")]
        initialise(dut)
        model = Machine()
        await edge(dut, rst_n=0, ena=0)
        model.edge(program, rst_n=False, ena=False)
        observe_shift_engine(dut, model)

        edge_bound = 2 + 8 * len(body)
        for _ in range(edge_bound):
            instruction = program[model.pc]
            sampled_inputs = 0
            if instruction.opcode == "SHIFT_STEP":
                index = 7 - model.shift_bits_done if msb_first else model.shift_bits_done
                sampled_inputs = ((received >> index) & 1) << instruction.rx_pin
            dut.engine_instruction.value = encode(instruction)
            dut.engine_instruction_valid.value = 1
            dut.engine_sampled_inputs.value = sampled_inputs
            dut.engine_tx_payload.value = payload
            if model.shift_active and model.shift_bits_done == 7:
                await Timer(1, unit="ns")
                expected_write = int(instruction.opcode == "SHIFT_STEP")
                assert int(dut.engine_shift_result_write.value) == expected_write
                if expected_write:
                    assert int(dut.engine_shift_result_data.value) == received
            await edge(dut)
            model.edge(program, sampled_inputs=sampled_inputs, tx_payload=payload)
            observe_shift_engine(dut, model)

        assert (model.state, model.pc, model.shift_result_write) == (
            State.HALT, len(program) - 1, False
        )
        if interleaved:
            assert (model.gpio_value & 4, model.gpio_oe & 4) == (4, 4)


@cocotb.test(skip=os.getenv("GATES") == "yes")
async def shift_invalid_partial_and_reset_fail_closed(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    dut.engine_tx_payload.value = 0xA5
    dut.engine_instruction_valid.value = 1

    dut.engine_instruction.value = encode(Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1))
    await edge(dut)
    assert (int(dut.engine_shift_active_status.value),
            int(dut.engine_shift_bits_done_status.value)) == (1, 1)
    held = (int(dut.engine_pc.value), int(dut.engine_gpio_value.value),
            int(dut.engine_gpio_oe.value), int(dut.engine_shift_bits_done_status.value))
    await edge(dut, ena=0)
    assert (int(dut.engine_pc.value), int(dut.engine_gpio_value.value),
            int(dut.engine_gpio_oe.value),
            int(dut.engine_shift_bits_done_status.value)) == held
    for _ in range(6):
        await edge(dut)
    assert (int(dut.engine_shift_active_status.value),
            int(dut.engine_shift_bits_done_status.value),
            int(dut.engine_shift_result_write.value)) == (1, 7, 1)
    dut.engine_instruction.value = encode(Instruction("HALT"))
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value)) == (3, 7)

    for invalid_word in (
        encode(Instruction("SHIFT_STEP", tx_pin=2, rx_pin=2)),
        encode(Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1)) | 1,
    ):
        await edge(dut, rst_n=0, ena=0)
        dut.engine_instruction.value = invalid_word
        dut.engine_instruction_valid.value = 1
        await edge(dut)
        assert (int(dut.engine_state.value), int(dut.engine_pc.value)) == (3, 0)
        assert (int(dut.engine_gpio_value.value), int(dut.engine_gpio_oe.value)) == (0, 0)

    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction.value = encode(Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1))
    dut.engine_instruction_valid.value = 1
    await edge(dut)
    assert int(dut.engine_shift_active_status.value) == 1
    await edge(dut, rst_n=0, ena=0)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value),
            int(dut.engine_shift_active_status.value),
            int(dut.engine_shift_result_write.value)) == (0, 0, 0, 0)

    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction.value = encode(Instruction("SHIFT_STEP", tx_pin=0, rx_pin=1))
    dut.engine_instruction_valid.value = 1
    await edge(dut)
    dut.engine_instruction.value = encode(
        Instruction("SHIFT_STEP", msb_first=1, tx_pin=0, rx_pin=1)
    )
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value)) == (3, 1)
    await edge(dut, rst_n=0, ena=0)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value),
            int(dut.engine_shift_active_status.value),
            int(dut.engine_shift_result_write.value)) == (0, 0, 0, 0)


@cocotb.test(skip=os.getenv("GATES") == "yes")
async def randomized_trace_matches_reviewed_model(dut):
    initialise(dut)
    rng = random.Random(SEED)
    program = [
        Instruction("SET", mask=0xF3, value=0xA1, oe=0xB2),
        Instruction("WAIT", count=0), Instruction("WAIT", count=1),
        Instruction("SET", mask=0x0F, value=0x05, oe=0x09),
        Instruction("WAIT", count=2), Instruction("HALT"),
    ]
    model = Machine()
    await edge(dut, rst_n=0, ena=0)
    model.edge(program, rst_n=False, ena=False)
    observe_engine(dut, model)
    for _ in range(40):
        if model.state is State.RUN and model.pc < len(program):
            dut.engine_instruction.value = encode(program[model.pc])
            dut.engine_instruction_valid.value = 1
        else:
            dut.engine_instruction.value = 3 << 30
            dut.engine_instruction_valid.value = int(model.pc < len(program))
        ena = rng.randrange(2)
        await edge(dut, ena=ena)
        model.edge(program, ena=bool(ena))
        observe_engine(dut, model)
    await edge(dut, rst_n=0, ena=0)
    model.edge(program, rst_n=False, ena=False)
    observe_engine(dut, model)


@cocotb.test(skip=os.getenv("GATES") == "yes")
async def invalid_encoding_and_out_of_range_fail_closed(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction.value = 0x01000000
    dut.engine_instruction_valid.value = 1
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value)) == (3, 0)
    assert (int(dut.engine_gpio_value.value), int(dut.engine_gpio_oe.value)) == (0, 0)
    await edge(dut, rst_n=0, ena=0)
    dut.engine_instruction_valid.value = 0
    await edge(dut)
    assert (int(dut.engine_state.value), int(dut.engine_pc.value)) == (3, 0)
