# SPDX-License-Identifier: Apache-2.0
"""Eight-word deletion controls and explicit real-loader capacity rejection."""
import json
import os
from pathlib import Path
import sys
import cocotb
from cocotb.triggers import Timer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test import edge, load_program, check_readback, write_data_register
from experiments.spi_phase.phase_programs import encode
from experiments.spi_phase.phase1_capacity import best_reference, deletions, evaluate
from tools.spi_four_mode_oracle import raw_at, assess

OUT = Path(os.environ["SPI_PHASE1_RECORD_DIR"])


def save(record, trace=None):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT/"cases.jsonl").open("a") as output:
        output.write(json.dumps(record, sort_keys=True)+"\n")
    if trace is not None:
        (OUT/(record["name"]+".json")).write_text(
            json.dumps({"case": record, "trace": trace}, separators=(",", ":"))+"\n")


async def transfer(dut, name, program, removed, mode, order):
    reference, expected_trace = evaluate(program, mode, order)
    assert len(program) == 8 and not reference["accepted"]
    schedule = reference["schedule"]
    words = [encode(w) for w in program]
    dut.clk.value=0; dut.ena.value=0; dut.rst_n.value=0
    dut.ui_in.value=0; dut.uio_in.value=0
    await edge(dut, rst_n=0, ena=0)
    await load_program(dut, words)
    await check_readback(dut, words)
    await write_data_register(dut, 1, 0x96)
    dut.ui_in.value=0; dut.uio_in.value=2
    await edge(dut, ena=0); await edge(dut, ena=0)
    trace=[{"edge":0,"out":0,"oe":0,"miso":1,"rx":0,"rx_valid":0,"state":"RUN"}]
    dut.ena.value=1
    for n in range(1, schedule["halt"]+1):
        await Timer(9999, unit="ps")
        raw=raw_at(n, schedule, 0x69, order, "held")
        dut.uio_in.value=raw<<1
        await Timer(1, unit="ps"); dut.clk.value=1
        await Timer(1, unit="ps")
        status=int(dut.uo_out.value)
        row={"edge":n,"out":int(dut.uio_out.value),"oe":int(dut.uio_oe.value),
             "miso":raw,"state":("RUN","WAIT","HALT","FAULT")[status>>6]}
        dut.ui_in.value=0x62; await Timer(1,unit="ps"); row["rx"]=int(dut.uo_out.value)
        dut.ui_in.value=0x63; await Timer(1,unit="ps"); row["rx_valid"]=int(dut.uo_out.value)
        dut.ui_in.value=0
        trace.append(row)
        await Timer(9997,unit="ps"); dut.clk.value=0
    errors=assess(trace,schedule,0x96,0x69,order,[s+24 for s in schedule["sample"]])
    if reference["cs"] is None:
        errors.append({"kind":"missing_cs","edge":0})
    record={"name":name,"mode":mode,"order":order,"removed_indices":list(removed),
            "words":[f"{w:08x}" for w in words],"kind":"EIGHT_WORD_DELETION",
            "accepted":not errors,"expected_rejection":True,
            "error_kinds":sorted({e["kind"] for e in errors}),
            "first_errors":errors[:4],"raw_rx":trace[-1]["rx"],
            "valid":trace[-1]["rx_valid"],"terminal":trace[-1]["state"],
            "all_observations_match_reference":trace==expected_trace}
    save(record,trace)
    assert errors and record["error_kinds"]==reference["error_kinds"],record
    assert trace==expected_trace,record


async def reject_oversized_commit(dut, mode, order):
    program=best_reference(mode,order)
    words=[encode(w) for w in program]
    dut.clk.value=0; dut.ena.value=0; dut.rst_n.value=0
    dut.ui_in.value=0; dut.uio_in.value=0
    await edge(dut,rst_n=0,ena=0)
    # Write only legal addresses. The nine/ten-word image is never aliased.
    await load_program(dut,words[:8])
    dut.ui_in.value=0xE0; dut.uio_in.value=len(words)
    await edge(dut)
    assert int(dut.uo_out.value)==0
    dut.ui_in.value=0xA0; await Timer(1,unit="ns")
    assert int(dut.uio_out.value)==0
    dut.ui_in.value=0; dut.uio_in.value=0
    observations=[]
    for _ in range(4):
        await edge(dut)
        row=[int(dut.uo_out.value),int(dut.uio_out.value),int(dut.uio_oe.value)]
        observations.append(row)
        assert row==[0,0,0]
    save({"name":f"m{mode}-o{order}-oversized-commit","kind":"CAPACITY_REJECTION",
          "mode":mode,"order":order,"declared_words":len(words),
          "legal_bytes_written":32,"accepted":False,"expected_rejection":True,
          "observations":observations})


@cocotb.test()
async def phase1_deletions_and_capacity(dut):
    for mode in (1,3):
        for order in (0,1):
            for name,program,removed in deletions(mode,order):
                await transfer(dut,name,program,removed,mode,order)
            await reject_oversized_commit(dut,mode,order)
