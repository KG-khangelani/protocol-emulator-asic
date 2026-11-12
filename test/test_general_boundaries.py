# SPDX-License-Identifier: Apache-2.0
"""Public storage, address, branch and serial-option boundaries for G2."""
import hashlib
import json
import os
from pathlib import Path
import random
import cocotb
from cocotb.triggers import Timer
from test import edge, initialise, write_data_register, read_data_register
from test_i2c_general_public import load_and_check, VARIANT
from experiments.i2c.general_programs import GeneralInstruction as I, encode

OUT = Path(os.environ["I2C_GENERAL_RECORD_DIR"])
CAPACITY = 128 if VARIANT == "od128" else 255
SEED = 20261112


def retain(name, observations):
    OUT.mkdir(parents=True, exist_ok=True)
    blob = (json.dumps(observations, sort_keys=True, separators=(",", ":"))+"\n").encode()
    (OUT/(name+".json")).write_bytes(blob)
    with (OUT/"boundaries.jsonl").open("a") as f:
        f.write(json.dumps({"name": name, "variant": VARIANT, "seed": SEED,
                            "observations": len(observations), "sha256": hashlib.sha256(blob).hexdigest()})+"\n")


async def runtime(dut, address):
    dut.ui_in.value = 0x60 | address
    await Timer(1, unit="ns")
    value = int(dut.uo_out.value)
    dut.ui_in.value = 0
    await Timer(1, unit="ns")
    return value


async def boot(dut, program, data=None, raw=0):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    await load_and_check(dut, [encode(w) for w in program], data or {})
    dut.uio_in.value = raw
    await edge(dut, ena=0)
    await edge(dut, ena=0)


@cocotb.test()
async def public_store_banks_lengths_and_reset(dut):
    initialise(dut)
    await edge(dut, rst_n=0, ena=0)
    rng = random.Random(SEED)
    words = [rng.getrandbits(32) for _ in range(CAPACITY)]
    await load_and_check(dut, words, {})
    observations = []
    for length in range(256):
        await write_data_register(dut, 0, length)
        ready = bool(int(dut.uo_out.value) & 32)
        actual = await read_data_register(dut, 0)
        assert ready == (1 <= length <= CAPACITY)
        assert actual == (length if ready else 0)
        observations.append(["length", length, ready, actual])
    banks = (CAPACITY+7)//8
    for bank in range(256):
        await write_data_register(dut, 0, CAPACITY)
        await write_data_register(dut, 5, bank)
        assert not int(dut.uo_out.value) & 32
        assert await read_data_register(dut, 0) == 0
        actual = await read_data_register(dut, 5)
        assert actual == (bank if bank < banks else 0)
        observations.append(["bank", bank, actual])
    # Every bank and byte lane retains its distinct word through length/bank writes.
    for index, word in enumerate(words):
        await write_data_register(dut, 5, index//8)
        for lane in range(4):
            dut.ui_in.value = 0x80 | (index%8)*4 | lane
            await Timer(1, unit="ns")
            actual = int(dut.uio_out.value)
            assert actual == word >> (8*lane) & 255
            observations.append(["byte", index, lane, actual])
    if CAPACITY == 255:
        await write_data_register(dut, 5, 31)
        for lane in range(4):
            dut.ui_in.value = 0xDC | lane
            dut.uio_in.value = 255
            await edge(dut)
            dut.ui_in.value = 0x9C | lane
            await Timer(1, unit="ns")
            assert int(dut.uio_out.value) == 0
        await write_data_register(dut, 5, 0)
        dut.ui_in.value = 0x80
        await Timer(1, unit="ns")
        assert int(dut.uio_out.value) == words[0] & 255
    await write_data_register(dut, 0, CAPACITY)
    for selector in (6, 7):
        await write_data_register(dut, selector, 255)
        assert int(dut.uo_out.value) & 32
        assert await read_data_register(dut, 0) == CAPACITY
    await edge(dut, rst_n=0, ena=0)
    for index in range(CAPACITY):
        await write_data_register(dut, 5, index//8)
        for lane in range(4):
            dut.ui_in.value = 0x80 | (index%8)*4 | lane
            await Timer(1, unit="ns")
            assert int(dut.uio_out.value) == 0
    retain("store-banks-lengths-reset", observations)


@cocotb.test()
async def public_pc_branch_and_skip_boundaries(dut):
    observations = []
    for count in (0, 1):
        for target in (31, 32, 63, 64, CAPACITY-1, CAPACITY, 255):
            program = [I("WAIT", count=0)] * CAPACITY
            program[0] = I("WAIT_PIN", pin=0, level=1, count=count, jump=target)
            program[-1] = I("HALT")
            await boot(dut, program)
            for _ in range(count+1):
                await edge(dut)
            pc = await runtime(dut, 6)
            assert pc == target
            await edge(dut)
            state = int(dut.uo_out.value) >> 6
            assert state == (3 if target >= CAPACITY else 2 if target == CAPACITY-1 else 0)
            observations.append(["branch", count, target, pc, state])
        if CAPACITY == 255:
            program = [I("WAIT", count=0)] * CAPACITY
            program[0] = I("WAIT_PIN", pin=0, level=1, count=0, jump=254)
            program[-1] = I("WAIT_PIN", pin=0, level=1, count=count, timeout_skip=True)
            await boot(dut, program)
            await edge(dut)
            for _ in range(count+1):
                await edge(dut)
            row = ["skip-overflow", count, await runtime(dut, 6), int(dut.uo_out.value) >> 6]
            observations.append(row)
            if row[3] != 3:
                retain("pc-branch-skip-partial", observations)
            assert row[3] == 3, row
    # Every full-width PC is observable; the final allocated word executes HALT.
    await boot(dut, [I("WAIT", count=0)]*(CAPACITY-1)+[I("HALT")])
    for index in range(CAPACITY):
        assert await runtime(dut, 6) == index
        assert int(dut.uo_out.value) & 31 == index & 31
        await edge(dut)
    assert int(dut.uo_out.value) >> 6 == 2
    retain("pc-branch-skip", observations)


@cocotb.test()
async def public_branch_abandons_partial_byte_and_loop(dut):
    observations = []
    for count in (0, 1, 7):
        for phase in (False, True):
            partial = I("DRIVE" if phase else "SHIFT_STEP", tx_pin=0, rx_pin=1,
                        msb_first=1, open_drain=VARIANT == "od128")
            program = [I("SET", mask=255, oe=0), I("LOOP", length=2, count=8), partial,
                       I("WAIT_PIN", pin=2, level=1, count=count, jump=5), I("HALT"),
                       I("LOOP", length=1, count=8), I("SHIFT_STEP", tx_pin=3, rx_pin=4, msb_first=1), I("HALT")]
            await boot(dut, program, {1: 0x96, 4: 0x69}, raw=16)
            for _ in range(3):
                await edge(dut)
            before = [int(dut.uio_out.value), int(dut.uio_oe.value)]
            await edge(dut)
            if count:
                frozen = [await runtime(dut, 6), int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)]
                for _ in range(4):
                    await edge(dut, ena=0)
                    assert [await runtime(dut, 6), int(dut.uo_out.value), int(dut.uio_out.value), int(dut.uio_oe.value)] == frozen
                for _ in range(count):
                    await edge(dut)
            assert await runtime(dut, 6) == 5
            assert [int(dut.uio_out.value), int(dut.uio_oe.value)] == before
            assert await runtime(dut, 3) == 0
            for _ in range(10):
                await edge(dut)
            assert int(dut.uo_out.value) >> 6 == 2
            assert await runtime(dut, 2) == 255 and await runtime(dut, 3) == 1
            observations.append([count, phase, before, await runtime(dut, 6)])
    retain("branch-abandons-partial", observations)


@cocotb.test()
async def public_open_drain_and_alternate_payload(dut):
    observations = []
    if VARIANT == "od128":
        for tx_pin, rx_pin in ((0, 1), (1, 0), (7, 6), (3, 4)):
            for value in (0, 1, 0x80, 0x96, 0xff):
                for order in (0, 1):
                    for alternate in (False, True):
                        for od in (False, True):
                            program = [I("SHIFT_STEP", tx_pin=tx_pin, rx_pin=rx_pin, msb_first=order,
                                         alternate=alternate if n == 0 else not alternate, open_drain=od)
                                       for n in range(8)] + [I("HALT")]
                            await boot(dut, program, {1: value, 4: value ^ 255}, raw=1 << rx_pin)
                            payload = value ^ (255 if alternate else 0)
                            trace = []
                            for bit in range(8):
                                await edge(dut)
                                expected = payload >> (7-bit if order else bit) & 1
                                out = int(dut.uio_out.value) >> tx_pin & 1
                                oe = int(dut.uio_oe.value) >> tx_pin & 1
                                assert (out, oe) == ((0, 1-expected) if od else (expected, 1))
                                assert not int(dut.uio_oe.value) & (1 << rx_pin)
                                assert await runtime(dut, 3) == int(bit == 7)
                                trace.append([out, oe])
                            assert await runtime(dut, 2) == 255
                            await edge(dut)
                            assert int(dut.uo_out.value) >> 6 == 2
                            observations.append([tx_pin, rx_pin, value, order, alternate, od, trace])
    retain("open-drain-alternate", observations)
