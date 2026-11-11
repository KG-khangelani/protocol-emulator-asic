# SPDX-License-Identifier: Apache-2.0
"""Core-tick public RTL screen; no internal DUT handles or widened loader."""
import json
import os
from pathlib import Path
import sys
import cocotb
from cocotb.triggers import Timer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, load_program, check_readback, write_data_register
from experiments.spi_phase.phase_programs import encode
from experiments.spi_phase.four_mode_programs import image
from tools.spi_four_mode_oracle import timing, raw_at, assess

OUT = Path(os.environ["SPI_FOUR_MODE_RECORD_DIR"])


async def transfer(dut, mode, order, family, profile, rx):
    tx=(73*rx+19)&255
    program,cs=image(mode,order,family)
    assert len(program)==8, "Never alias an oversized reference through public addresses"
    words=[encode(w) for w in program]
    schedule=timing(mode,cs)
    captures=[s+(24 if family=="held" else 2) for s in schedule["sample"]]
    dut.clk.value=0; dut.ena.value=0; dut.rst_n.value=0
    dut.ui_in.value=0; dut.uio_in.value=0
    await edge(dut,rst_n=0,ena=0)
    await load_program(dut,words)
    await check_readback(dut,words)
    await write_data_register(dut,1,tx)
    dut.ui_in.value=0; dut.uio_in.value=2
    await edge(dut,ena=0); await edge(dut,ena=0)
    trace=[{"edge":0,"out":0,"oe":0,"miso":1,"rx":0,"rx_valid":0,"state":"RUN"}]
    dut.ena.value=1
    for n in range(1,schedule["halt"]+1):
        await Timer(9999,unit="ps")
        raw=raw_at(n,schedule,rx,order,profile)
        dut.uio_in.value=raw<<1
        await Timer(1,unit="ps"); dut.clk.value=1
        await Timer(1,unit="ps")
        status=int(dut.uo_out.value)
        row={"edge":n,"out":int(dut.uio_out.value),"oe":int(dut.uio_oe.value),
             "miso":raw,"state":("RUN","WAIT","HALT","FAULT")[status>>6]}
        dut.ui_in.value=0x62; await Timer(1,unit="ps"); row["rx"]=int(dut.uo_out.value)
        dut.ui_in.value=0x63; await Timer(1,unit="ps"); row["rx_valid"]=int(dut.uo_out.value)
        dut.ui_in.value=0
        trace.append(row)
        await Timer(9997,unit="ps"); dut.clk.value=0
    errors=assess(trace,schedule,tx,rx,order,captures)
    expected=(family=="held" and profile=="held") or (family=="naive" and mode==0)
    record={"mode":mode,"order":order,"family":family,"profile":profile,"tx":tx,"rx":rx,
            "words":[f"{w:08x}" for w in words],"expected_acceptance":expected,
            "accepted":not errors,"error_kinds":sorted({e["kind"] for e in errors}),
            "first_errors":errors[:4],"raw_rx":trace[-1]["rx"],"halt":trace[-1]["state"],
            "scope":"ACTUAL_PUBLIC_LOADED_COMPACT_CORE_TICK_SCREEN"}
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"cases.jsonl").open("a") as f: f.write(json.dumps(record,sort_keys=True)+"\n")
    if not expected or rx==0x69:
        name=f"{family}-{profile}-m{mode}-o{order}-r{rx:02x}"
        (OUT/(name+".json")).write_text(json.dumps({"case":record,"trace":trace},indent=2)+"\n")
    assert (not errors)==expected,record
    if family=="held" and profile=="edge_only":
        assert record["raw_rx"]==rx^255 and record["error_kinds"]==["received_byte"],record
    if family=="naive" and mode==2:
        assert record["raw_rx"]==rx and record["error_kinds"]==["idle_before_cs"],record


@cocotb.test()
async def fitting_images_and_boundary_controls(dut):
    for mode in (0,2):
        for order in (0,1):
            for rx in (0,1,0x69,0x96,0xFE,0xFF):
                await transfer(dut,mode,order,"held","held",rx)
            await transfer(dut,mode,order,"held","edge_only",0x69)
    for mode in range(4):
        for order in (0,1):
            await transfer(dut,mode,order,"naive","held",0x69)
