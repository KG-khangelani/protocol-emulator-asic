# SPDX-License-Identifier: Apache-2.0
"""Public transactions and independent instruction/lifecycle checks."""
import hashlib
import json
import os
from pathlib import Path
import sys
import cocotb
from cocotb.triggers import Timer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test import edge, initialise, write_data_register, STATE_BITS, G2_CURRENT
from experiments.spi_phase.timed_gpio_programs import (
    TimedInstruction as I, TimedMachine, image, encode, evaluate, public_cases, MIXED)
from tools.m1_contract_model import State
from tools.spi_four_mode_oracle import timing, raw_at, assess

VARIANT=os.environ["TIMED_GPIO_VARIANT"]
OUT=Path(os.environ["TIMED_GPIO_RECORD_DIR"])
SMOKE=os.getenv("TIMED_GPIO_SMOKE")=="1"

def save(record,trace=None,*,control=False):
    OUT.mkdir(parents=True,exist_ok=True)
    if trace is not None:
        blob=(json.dumps(trace,separators=(",",":"))+"\n").encode()
        record["trace_sha256"]=hashlib.sha256(blob).hexdigest()
        # Retain corner/negative traces; all transaction trace hashes are recorded.
        if any(label in record["name"] for label in ("early","late","mixed","edge-only","held")):
            (OUT/(record["name"]+".json")).write_bytes(blob)
    with (OUT/("controls.jsonl" if control else "cases.jsonl")).open("a") as f:
        f.write(json.dumps(record,sort_keys=True)+"\n")

async def load_and_check(dut,words):
    assert len(words)<=(10 if VARIANT=="compact10" else 8)
    bank=0
    for index,word in enumerate(words):
        desired=index//8
        if bank!=desired:
            await write_data_register(dut,5,desired);bank=desired
        for lane in range(4):
            dut.ui_in.value=0xC0|((index%8)*4+lane)
            dut.uio_in.value=(word>>(8*lane))&255
            await edge(dut)
            assert int(dut.uio_oe.value)==0
    await write_data_register(dut,0,len(words))
    bank=0
    for index,word in enumerate(words):
        desired=index//8
        if bank!=desired:
            await write_data_register(dut,5,desired);bank=desired
        for lane in range(4):
            dut.ui_in.value=0x80|((index%8)*4+lane)
            await Timer(1,unit="ns")
            assert int(dut.uio_out.value)==((word>>(8*lane))&255)
    await write_data_register(dut,0,len(words))
    assert int(dut.uo_out.value)&32

async def prepare(dut,program,tx=0x96):
    initialise(dut)
    await edge(dut,rst_n=0,ena=0)
    await load_and_check(dut,[encode(w,VARIANT) for w in program])
    await write_data_register(dut,1,tx)
    dut.ui_in.value=0;dut.uio_in.value=2
    await edge(dut,ena=0);await edge(dut,ena=0)

async def transfer(dut,name,mode,order,tx,rx,responses,profile="held"):
    program,expected,reference_errors=evaluate(VARIANT,mode,order,tx,rx,responses,profile)
    schedule=timing(mode,2 if mode&1 else 3)
    await prepare(dut,program,tx)
    trace=[{"edge":0,"out":0,"oe":0,"miso":1,"rx":0,"rx_valid":0,"state":"RUN"}]
    dut.ena.value=1
    for n in range(1,schedule["halt"]+1):
        await Timer(9999,unit="ps")
        raw=raw_at(n,schedule,rx,order,profile,responses)
        dut.uio_in.value=raw<<1
        await Timer(1,unit="ps");dut.clk.value=1
        await Timer(1,unit="ps")
        status=int(dut.uo_out.value)
        row={"edge":n,"out":int(dut.uio_out.value),"oe":int(dut.uio_oe.value),"miso":raw,
             "state":("RUN","WAIT","HALT","FAULT")[status>>6]}
        dut.ui_in.value=0x62;await Timer(1,unit="ps");row["rx"]=int(dut.uo_out.value)
        dut.ui_in.value=0x63;await Timer(1,unit="ps");row["rx_valid"]=int(dut.uo_out.value)
        dut.ui_in.value=0;trace.append(row)
        await Timer(9997,unit="ps");dut.clk.value=0
    errors=assess(trace,schedule,tx,rx,order,[s+24 for s in schedule["sample"]])
    kinds=sorted({e["kind"] for e in errors})
    record={"name":name,"mode":mode,"order":order,"tx":tx,"rx":rx,"words":len(program),
            "profile":profile,"accepted":not errors,"error_kinds":kinds,
            "reference_equal":trace==expected,
            "contract_trace_sha256":hashlib.sha256(json.dumps(
                [{k:v for k,v in row.items() if k!="state"} for row in trace],
                separators=(",",":")).encode()).hexdigest()}
    save(record,trace)
    assert trace==expected,(name,next((n for n,(a,b) in enumerate(zip(trace,expected)) if a!=b),None))
    assert kinds==sorted({e["kind"] for e in reference_errors}),record
    assert kinds==(["received_byte"] if profile=="edge_only" else []),record

@cocotb.test()
async def timed_public_programs(dut):
    count=0
    for name,mode,order,tx,rx,responses in public_cases():
        if SMOKE and not any(x in name for x in ("early","late","mixed")):continue
        await transfer(dut,name,mode,order,tx,rx,responses);count+=1
    assert count==(12 if SMOKE else 1036)
    for mode in (1,3):
        for order in (0,1):
            await transfer(dut,f"m{mode}-o{order}-edge-only",mode,order,0x96,0x69,MIXED,"edge_only")
    for mode in (0,2):
        for order in (0,1):
            for label,tx,rx,response in (("early",0x96,0x69,[1]*8),("late",0,255,[96]*8),
                                        ("mixed",255,0,MIXED)):
                await transfer(dut,f"held-m{mode}-o{order}-{label}",mode,order,tx,rx,response)

def core_observe(dut,model):
    for port,expected in [
        ("pc",model.pc),("state",STATE_BITS[model.state]),("wait_left",model.wait_left),
        ("gpio_value",model.gpio_value),("gpio_oe",model.gpio_oe),
        ("loop_active_status",model.loop_active),("loop_remaining_status",model.loop_remaining),
        ("shift_active_status",model.shift_active),("shift_bits_done_status",model.shift_bits_done),
        ("shift_tx_data_status",model.shift_tx_data),("shift_rx_data_status",model.shift_rx_data),
        ("shift_period_status",model.shift_period)]:
        assert int(getattr(dut,"engine_"+port).value)==int(expected),(port,expected,model)
    assert int(dut.engine_shift_result_write.value)==0

async def core_program(dut,program,*,mutate=True,reset_cut=None):
    initialise(dut);model=TimedMachine(variant=VARIANT)
    await edge(dut,rst_n=0,ena=0);model.edge(program,rst_n=False,ena=False)
    n=0
    while model.state not in (State.HALT,State.FAULT) and n<500:
        dut.engine_instruction_valid.value=1
        waiting=model.state==State.WAIT
        dut.engine_instruction.value=(0xffffffff if waiting and mutate else encode(program[model.pc],VARIANT))
        dut.engine_tx_payload.value=0xA6
        ena=not(waiting and n%3==0)
        if reset_cut is not None and waiting and model.wait_left==reset_cut:
            await edge(dut,rst_n=0,ena=0);model.edge(program,rst_n=False,ena=False)
            core_observe(dut,model);return
        await edge(dut,ena=int(ena))
        model.edge(program,ena=ena,tx_payload=0xA6)
        core_observe(dut,model);n+=1
    assert n<500
    assert model.state==State.HALT

@cocotb.test()
async def timed_instruction_and_abort_controls(dut):
    if G2_CURRENT:
        assert VARIANT == "compact10"
        # The same compact10 software executes on a real 128-word store. A
        # write in its final bank must not disturb the first two banks.
        words = [0x10203040 + i * 0x01010101 for i in range(10)]
        initialise(dut)
        await edge(dut, rst_n=0, ena=0)
        await load_and_check(dut, words)
        await write_data_register(dut, 5, 15)
        tail = 0x91827364
        for lane in range(4):
            dut.ui_in.value = 0xDC | lane
            dut.uio_in.value = (tail >> (8 * lane)) & 255
            await edge(dut)
        observations = []
        for index, word in [*enumerate(words), (127, tail)]:
            await write_data_register(dut, 5, index // 8)
            for lane in range(4):
                dut.ui_in.value = 0x80 | (index % 8) * 4 | lane
                await Timer(1, unit="ns")
                actual = int(dut.uio_out.value)
                assert actual == (word >> (8 * lane)) & 255
                observations.append([index, lane, actual])
        await write_data_register(dut, 5, 16)
        dut.ui_in.value = 0xA5
        await Timer(1, unit="ns")
        assert int(dut.uio_out.value) == 0 and not int(dut.uo_out.value) & 32
        save({"name": "current-banked-nonalias", "accepted": True,
              "observations": observations, "invalid_bank": 16}, control=True)
        return
    if VARIANT=="compact10":
        # Matched banked baseline: address32..39 work and out-of-range bank1
        # writes cannot alias the actual ten words.
        words=[0x10203040+i*0x01010101 for i in range(10)]
        initialise(dut);await edge(dut,rst_n=0,ena=0)
        await load_and_check(dut,words)
        await write_data_register(dut,5,1)
        for addr in range(8,32):
            dut.ui_in.value=0xC0|addr;dut.uio_in.value=0xff;await edge(dut)
            dut.ui_in.value=0x80|addr;await Timer(1,unit="ns")
            assert int(dut.uio_out.value)==0
        await write_data_register(dut,5,0)
        # Read back without writing the image again.
        for index,word in enumerate(words):
            if index==8:await write_data_register(dut,5,1)
            for lane in range(4):
                dut.ui_in.value=0x80|((index%8)*4+lane);await Timer(1,unit="ns")
                assert int(dut.uio_out.value)==((word>>(8*lane))&255)
        save({"name":"banked-nonalias","accepted":True});return
    prefix=I("SET",mask=255,value=0xA5,oe=0xF0)
    halt=I("HALT")
    combinations=[(d,b) for d in range(64 if VARIANT=="P" else 32)
                  for b in ((False,True) if VARIANT=="F" else (False,))]
    count=0
    for delay,before in combinations:
        for mask in (0,0x0f,0x55,0xff):
            op=I("SET",mask=mask,value=0x3C,oe=0xA5,delay=delay,before=before)
            await core_program(dut,[prefix,I("LOOP",length=1,count=2),op,halt])
            count+=1
    if VARIANT=="P":
        for delay in range(0,29,4):
            program=[I("LOOP",length=2,count=8),
                     I("DRIVE",mask=4,value=4,tx_pin=0,rx_pin=1,msb_first=1,delay=delay),
                     I("SAMPLE",tx_pin=0,rx_pin=1,msb_first=1),halt]
            # This sequence has real RX commits; use public tests for byte behavior.
            # Single prepared DRIVE followed by reset tests delay at every cut.
            for cut in range(1,delay+1):
                await core_program(dut,[program[1],halt],reset_cut=cut)
    for before in ((False,True) if VARIANT=="F" else (False,)):
        maximum=63 if VARIANT=="P" else 31
        program=[prefix,I("SET",mask=0x5A,value=0xFF,oe=0x0F,delay=maximum,before=before),halt]
        for cut in range(1,maximum+1):
            await core_program(dut,program,reset_cut=cut)
    # Out-of-range fetch remains rejected even though the old test's first
    # reserved SET assertion intentionally fails before reaching this check.
    initialise(dut);await edge(dut,rst_n=0,ena=0)
    dut.engine_instruction_valid.value=0;await edge(dut)
    assert int(dut.engine_state.value)==3
    # Other phase-invalid encodings remain rejected.
    drive=encode(I("DRIVE",tx_pin=0,rx_pin=1),VARIANT)
    sample=encode(I("SAMPLE",tx_pin=0,rx_pin=1),VARIANT)
    invalid=[sample|1,drive|(1<<20),drive|(1<<11),drive|(2<<11)]
    if VARIANT=="F":invalid.append(drive|1)
    for word in invalid:
        initialise(dut);await edge(dut,rst_n=0,ena=0)
        dut.engine_instruction.value=word;dut.engine_instruction_valid.value=1;await edge(dut)
        assert int(dut.engine_state.value)==3
        assert int(dut.engine_gpio_oe.value)==0
    # Public loader entry cancels pending GPIO on every wait cut, including1.
    for before in ((False,True) if VARIANT=="F" else (False,)):
        program=[prefix,I("SET",mask=255,value=0x5A,oe=255,delay=7,before=before),halt]
        for cut in range(1,8):
            await prepare(dut,program)
            for _ in range(2+7-cut):await edge(dut)
            dut.ui_in.value=0x80;await edge(dut)
            dut.ui_in.value=0;await Timer(1,unit="ns")
            assert int(dut.uio_out.value)==0 and int(dut.uio_oe.value)==0
            dut.ena.value=0;await edge(dut,ena=0)
            assert int(dut.uio_out.value)==0 and int(dut.uio_oe.value)==0
    save({"name":"instruction-controls","accepted":True,"delay_mask_loop_cases":count})
