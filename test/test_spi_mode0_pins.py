# SPDX-License-Identifier: Apache-2.0
"""Complete compact mode-0 image; all DUT stimulus/observations are public pins."""

import json
import os
from pathlib import Path
import random
import sys

import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test import edge,load_program,check_readback,write_data_register
from experiments.spi_phase.pin_timing import (CAPTURE,FALLING,HALT,PERIOD_PS,RELEASE,RISING,
    assemble,envelope_errors,event_hash,events,gpio,literal_image,response_errors,wire_word)

OUT=Path(os.environ['SPI_PIN_RECORD_DIR'])


async def prepare(dut,tx,order,early):
    dut.clk.value=0; dut.ena.value=0; dut.rst_n.value=0
    dut.ui_in.value=0; dut.uio_in.value=0
    await edge(dut,rst_n=0,ena=0)
    words=literal_image(order,early=early)
    await load_program(dut,words)
    await check_readback(dut,words)
    await write_data_register(dut,1,tx)
    dut.ui_in.value=0; dut.uio_in.value=2
    await edge(dut,ena=0); await edge(dut,ena=0)
    assert (int(dut.uo_out.value),int(dut.uio_out.value),int(dut.uio_oe.value))==(0x20,0,0)


async def transact(dut,name,tx,rx,order,responses,*,noise=False,setup_ps=1,hold_ps=1,
                   early=False,abort=None,require=True,retain=False):
    changes=events(rx,order,responses,noise=noise,hold_ps=hold_ps)
    aperture=envelope_errors(changes,rx,order,setup_ps=setup_ps,hold_ps=hold_ps)
    response_violations=response_errors(responses,setup_ps=setup_ps)
    await prepare(dut,tx,order,early)
    base=int(get_sim_time(unit='ps'))
    timeline=[(t,0,'raw',v) for t,v in changes if t<=HALT*PERIOD_PS+4]
    for n in range(1,HALT+1):
        timeline += [(n*PERIOD_PS-10000,1,'fall',n),(n*PERIOD_PS,1,'rise',n),
                     (n*PERIOD_PS+1,2,'observe',n)]
    for n in (378,379):
        timeline += [(n*PERIOD_PS+2,1,'select_valid',n),(n*PERIOD_PS+3,2,'valid',n),
                     (n*PERIOD_PS+4,1,'select_raw',n)]
    timeline += [(HALT*PERIOD_PS+2,1,'select_status',0),(HALT*PERIOD_PS+3,2,'status',0)]
    if abort:
        kind,cut=abort
        timeline += [(cut*PERIOD_PS-2,1,'abort',kind),(cut*PERIOD_PS+2,1,'resume',kind)]
    dut.ena.value=1; dut.ui_in.value=0x62
    raw=1; raw_at_edge={}; observed=[]; rising=[]; falling=[]; cs=[]
    wire_tx=[]; wire_rx=[]; errors=[]; valids={}; final_raw=0; status=None
    old_resolved=8
    for t,priority,kind,arg in sorted(timeline):
        delta=base+t-int(get_sim_time(unit='ps'))
        assert delta>=0,(name,t,delta)
        if delta: await Timer(delta,unit='ps')
        if kind=='raw': raw=arg; dut.uio_in.value=raw<<1
        elif kind=='fall': dut.clk.value=0
        elif kind=='rise': raw_at_edge[arg]=raw; dut.clk.value=1
        elif kind=='select_valid': dut.ui_in.value=0x63
        elif kind=='select_raw': dut.ui_in.value=0x62
        elif kind=='select_status': dut.ui_in.value=0
        elif kind=='abort':
            if arg=='reset': dut.rst_n.value=0
            else: dut.ena.value=0
        elif kind=='resume': dut.rst_n.value=1; dut.ena.value=1
        elif kind=='valid':
            valids[str(arg)]=int(dut.uo_out.value)
            if valids[str(arg)]!=int(arg>=CAPTURE[-1]): errors.append([arg,'valid',valids[str(arg)]])
        elif kind=='status': status=int(dut.uo_out.value)
        elif kind=='observe':
            n=arg; value=int(dut.uio_out.value); oe=int(dut.uio_oe.value)
            current=int(dut.uo_out.value); expected=gpio(n,tx,order)
            if (value,oe)!=expected: errors.append([n,'gpio',value,oe,*expected])
            assert oe&2==0,(name,n,'MISO contention')
            if current!=(rx if n>=CAPTURE[-1] else 0): errors.append([n,'raw',current])
            resolved=(value&oe)|(8&~oe)
            if not old_resolved&4 and resolved&4:
                rising.append(n); wire_tx.append(value&1); wire_rx.append(raw_at_edge[n])
            if old_resolved&4 and not resolved&4: falling.append(n)
            if (old_resolved^resolved)&8: cs.append([n,(resolved>>3)&1])
            old_resolved=resolved
            observed.append({'edge':n,'time_ps':t,'out':value,'oe':oe,'miso_at_core_edge':raw_at_edge[n],'raw_rx':current})
            final_raw=current
    decoded_tx=assemble(wire_tx,order) if len(wire_tx)==8 else None
    decoded_rx=assemble(wire_rx,order) if len(wire_rx)==8 else None
    pins_ok=rising==RISING and falling==FALLING and cs==[[2,0],[RELEASE,1]] and decoded_tx==tx
    if pins_ok: assert decoded_rx==wire_word(changes,order),(name,'event/pin oracle disagreement')
    accepted=not aperture and not response_violations and not errors and pins_ok and decoded_rx==rx==final_raw and valids.get('379')==1 and status==0xA7
    record={'case':name,'tx':tx,'rx':rx,'order':order,'responses_ps':responses,'noise':noise,
        'setup_ps':setup_ps,'hold_ps':hold_ps,'early_sample_firmware':early,'abort':abort,
        'event_sha256':event_hash(changes),'event_count':len(changes),'aperture_violations':aperture,
        'response_profile_violations':response_violations,
        'wire_tx':decoded_tx,'wire_rx':decoded_rx,'raw_rx':final_raw,'valid_probes':valids,'status':status,
        'pin_schedule_ok':pins_ok,'accepted':accepted,'errors':errors[:12]}
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/'cases.jsonl').open('a') as f: f.write(json.dumps(record,sort_keys=True)+'\n')
    if retain or not require:
        (OUT/(name+'.json')).write_text(json.dumps({**record,'events':changes,'rising':rising,
            'falling':falling,'cs':cs,'observations':observed},indent=2)+'\n')
    if require: assert accepted,record
    return record


@cocotb.test()
async def mode0_alphabet_at_last_digital_setup(dut):
    for order in (0,1):
        for rx in range(256):
            await transact(dut,f'alphabet-{order}-{rx:02x}',255-rx,rx,order,[499999]*8,retain=rx==0x69)
    dut._log.info('SPI_PINS alphabet: 512 complete public-loaded transfers PASS')


@cocotb.test()
async def mode0_original_envelope_phase_sweep_and_jitter(dut):
    for order in (0,1):
        for d in range(1,97):
            await transact(dut,f'quarter-{order}-{d}',0x96,0x69,order,[5000*d]*8,
                           setup_ps=20000,hold_ps=20000,retain=d in (1,96))
        rng=random.Random(20261103+order)
        for k in range(32):
            response=[5000*rng.randint(1,96) for _ in range(8)]
            await transact(dut,f'original-jitter-{order}-{k}',rng.randrange(256),rng.randrange(256),order,
                           response,setup_ps=20000,hold_ps=20000)
    dut._log.info('SPI_PINS original envelope: 256 response-phase/jitter transfers PASS')


@cocotb.test()
async def mode0_noise_outside_aperture_and_boundary_offsets(dut):
    setups=(1,2,4999,5000,5001,19999,20000,20001,59999,60000,60001,480000)
    for order in (0,1):
        rng=random.Random(20261104+order)
        for k in range(32):
            await transact(dut,f'noise-{order}-{k}',rng.randrange(256),rng.randrange(256),order,
                           [rng.choice((1,5000,20001,480000,499999)) for _ in range(8)],noise=True,retain=k==0)
        for setup in setups:
            await transact(dut,f'boundary-{order}-{setup}',0x96,0x69,order,[500000-setup]*8,
                           setup_ps=setup,hold_ps=1)
    dut._log.info('SPI_PINS digital stress: 88 noise/boundary transfers PASS')


@cocotb.test()
async def mode0_preserved_program_and_envelope_counterexamples(dut):
    for order,wrong in ((0,0xD3),(1,0xB4)):
        r=await transact(dut,f'early-sample-{order}',0x96,0x69,order,[499999]*8,early=True,require=False)
        assert r['pin_schedule_ok'] and not r['aperture_violations']
        assert r['wire_rx']==0x69 and r['raw_rx']==wrong and not r['accepted']
        assert r['valid_probes']['378']==1
        r=await transact(dut,f'outside-envelope-{order}',0x96,0x69,order,[500001]*8,require=False)
        assert r['aperture_violations'] and not r['accepted'] and r['wire_rx']!=0x69
        assert r['raw_rx']==r['wire_rx'] and r['pin_schedule_ok']
        r=await transact(dut,f'outside-masked-{order}',0x96,0xFF,order,[500001]*8,require=False)
        assert r['raw_rx']==r['wire_rx']==0xFF and not r['accepted']
        assert not r['aperture_violations'] and r['response_profile_violations']==list(range(8))
    for kind,cut in (('stall',27),('reset',379)):
        r=await transact(dut,f'interruption-{kind}',0x96,0x69,1,[499999]*8,abort=(kind,cut),require=False)
        assert not r['accepted'] and r['status']!=0xA7 and not r['pin_schedule_ok']
    dut._log.info('SPI_PINS controls: 2 early-capture mismatches,4 envelope rejections,2 interrupted transactions retained')
