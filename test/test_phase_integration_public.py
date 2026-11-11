# SPDX-License-Identifier: Apache-2.0
"""Actual compact top only: all stimulus and observations use public pins."""

from pathlib import Path
import sys

import cocotb
from cocotb.triggers import Timer

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, load_program, check_readback, write_data_register
from test_spi_mode0_public import read_result


def image(order):
    return [0x62000008,0xA0480000|(order<<28),0xA0500018|(order<<28),0x80000000]


def bit(byte,index,order):
    return (byte>>(7-index if order else index))&1


async def read_register(dut,address):
    before=int(dut.uio_out.value),int(dut.uio_oe.value)
    dut.ui_in.value=0x60|address
    await Timer(1,unit='ns')
    result=int(dut.uo_out.value)
    assert (int(dut.uio_out.value),int(dut.uio_oe.value))==before
    return result


async def flush(dut,rx,order):
    dut.ui_in.value=0
    dut.uio_in.value=bit(rx,0,order)<<1
    await edge(dut,ena=0)
    await edge(dut,ena=0)


async def prepare(dut,tx,rx,order):
    initialise(dut)
    await edge(dut,rst_n=0,ena=0)
    await load_program(dut,image(order))
    await check_readback(dut,image(order))
    await write_data_register(dut,1,tx)
    await flush(dut,rx,order)
    assert await read_result(dut)==(0,0)


async def run_byte(dut,tx,rx,order,*,until=42,old_rx=0,old_valid=0):
    for q in range(1,until+1):
        index=min(max(q-2,0)//5,7)
        dut.uio_in.value=bit(rx,index,order)<<1
        dut.ui_in.value=0x61 if q%3==0 else 0x62
        await edge(dut)
        expected_tx=bit(tx,index,order) if q>=2 else 0
        assert (int(dut.uio_out.value),int(dut.uio_oe.value))==(expected_tx,1 if q>=2 else 0),q
        if q%3==0:
            assert int(dut.uo_out.value)==tx
        else:
            assert int(dut.uo_out.value)==(rx if q>=41 else old_rx),(q,rx,old_rx)
        if q in (40,41,42):
            assert await read_result(dut)==((rx,1) if q>=41 else (old_rx,old_valid)),q
    if until==42:
        dut.ui_in.value=0
        await Timer(1,unit='ns')
        assert int(dut.uo_out.value)==0xA3


async def abort(dut,kind,enabled):
    if kind=='reset':
        dut.ui_in.value=0
        await edge(dut,rst_n=0,ena=enabled)
    elif kind=='write':
        dut.ui_in.value=0xC0
        dut.uio_in.value=0xFF
        await edge(dut,ena=enabled)
    else:
        dut.ui_in.value=0xA2
        dut.uio_in.value=0
        await edge(dut,ena=enabled)
        assert int(dut.uio_oe.value)==255
    dut.ui_in.value=0
    await Timer(1,unit='ns')
    ready=kind!='reset' and not(kind=='write' and enabled)
    assert int(dut.uo_out.value)==(0x20 if ready else 0)
    assert (int(dut.uio_out.value),int(dut.uio_oe.value))==(0,0)


@cocotb.test()
async def public_capture_visibility_and_all_payloads(dut):
    for order in (0,1):
        for rx in range(256):
            tx=255-rx
            await prepare(dut,tx,rx,order)
            await run_byte(dut,tx,rx,order)
            assert await read_result(dut)==(rx,1)
    dut._log.info('INTEGRATION: 512 public loaded/read-back byte transfers PASS')


@cocotb.test()
async def public_abort_all_cuts_and_enable_priority(dut):
    for order in (0,1):
        for cut in range(2,42):
            for kind in ('read','write','reset'):
                for enabled in (0,1):
                    await prepare(dut,0x96,0x69,order)
                    await run_byte(dut,0x96,0x69,order,until=cut-1)
                    await abort(dut,kind,enabled)
                    assert await read_result(dut)==(0,0),(order,cut,kind,enabled)
                    for _ in range(2): await edge(dut,ena=0)
                    assert await read_result(dut)==(0,0)
    dut._log.info('INTEGRATION: 480 public abort cases PASS, cuts2..41/kinds3/enable2/orders2')


@cocotb.test()
async def old_result_survives_loader_abort_and_payload_invalidates(dut):
    for order in (0,1):
        for cut in (3,6,40,41):
            for kind in ('read','write','reset'):
                for enabled in (0,1):
                    await prepare(dut,0x96,0x69,order)
                    await run_byte(dut,0x96,0x69,order)
                    # Restart without a payload write; raw-valid intentionally stays one.
                    dut.ui_in.value=0xA2
                    dut.uio_in.value=0
                    await edge(dut,ena=0)
                    assert (int(dut.uio_out.value),int(dut.uio_oe.value))==(0x69,255)
                    await flush(dut,0x96,order)
                    await run_byte(dut,0x96,0x96,order,until=cut-1,old_rx=0x69,old_valid=1)
                    await abort(dut,kind,enabled)
                    expected=(0,0) if kind=='reset' else (0x69,1)
                    assert await read_result(dut)==expected,(order,cut,kind,enabled)
                    if kind!='reset':
                        await write_data_register(dut,4,0xA5)
                        dut.ui_in.value=0
                        await Timer(1,unit='ns')
                        assert await read_result(dut)==(0x69,0)
    dut._log.info('INTEGRATION: 48 retained-old-result abort/invalidation cases PASS')


@cocotb.test()
async def public_reset_erases_storage_and_loader_owns_read_bus(dut):
    await prepare(dut,0xA5,0x3C,1)
    await run_byte(dut,0xA5,0x3C,1)
    dut.ui_in.value=0xA2
    await edge(dut,rst_n=0,ena=0)
    assert (int(dut.uio_out.value),int(dut.uio_oe.value))==(0,255)
    # Reset clears logical GPIO, but the selected loader read still drives the bus.
    for address in range(32):
        dut.ui_in.value=0x80|address
        await Timer(1,unit='ns')
        assert (int(dut.uio_out.value),int(dut.uio_oe.value))==(0,255)
    for address in range(5):
        dut.ui_in.value=0xA0|address
        await Timer(1,unit='ns')
        assert int(dut.uio_out.value)==0
    dut.ui_in.value=0
    await Timer(1,unit='ns')
    assert (int(dut.uo_out.value),int(dut.uio_out.value),int(dut.uio_oe.value))==(0,0,0)
