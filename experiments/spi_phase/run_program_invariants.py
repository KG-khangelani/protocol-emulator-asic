# SPDX-License-Identifier: Apache-2.0
"""One resource-limited actual loaded-program induction attempt, no retries."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import subprocess
import time
from build_variants import ROOT,FILES,build,once
from legacy_baseline import baseline_inputs
from run_formal import PORTS,digest,instrument
from run_integration import readouts

EXPORTS={**PORTS,'formal_phase_active':1,'formal_phase_prepared':1,'formal_program_bits':256,
    'formal_sync_meta':8,'sampled_inputs':8,'tx_payload':8,'tx_payload_alt':8,'rx_result':8,'rx_valid':1,
    'program_length':4,'program_ready':1,'instruction':32,'instruction_valid':1}

def prepare(out):
    sources=build(out/'variants'); src=out/'variants/compact/src'; inputs=out/'inputs'; inputs.mkdir()
    engine=readouts(instrument((src/'m1_engine.v').read_text()),[
        ('    assign formal_phase_active = phase_active;\n    assign formal_phase_prepared = phase_prepared;\n    reg phase_active;\n    reg phase_prepared;',
         '    reg phase_active;\n    reg phase_prepared;\n    assign formal_phase_active = phase_active;\n    assign formal_phase_prepared = phase_prepared;')], 'phase-engine-declarations.v',inputs)
    (inputs/'phase_engine.v').write_text(engine)
    store=readouts((src/'m1_program_store.v').read_text(),[
        ('    output wire instruction_valid\n','    output wire instruction_valid, output wire [255:0] formal_program_bits\n'),
        ('    reg [31:0] word4, word5, word6, word7;','    reg [31:0] word4, word5, word6, word7;\n    assign formal_program_bits={word7,word6,word5,word4,word3,word2,word1,word0};')], 'm1_program_store.v',inputs)
    (inputs/'m1_program_store.v').write_text(store)
    sync=readouts((src/'m1_input_sync.v').read_text(),[
        ('    output reg [7:0] sampled_in\n','    output reg [7:0] sampled_in, output wire [7:0] formal_meta\n'),
        ('    reg [7:0] metastability_stage;','    reg [7:0] metastability_stage;\n    assign formal_meta=metastability_stage;')], 'm1_input_sync.v',inputs)
    (inputs/'m1_input_sync.v').write_text(sync)
    (inputs/'m1_data_store.v').write_bytes((src/'m1_data_store.v').read_bytes())
    ports=',\n'.join('    output wire '+(f'[{w-1}:0] ' if w>1 else '')+'f_'+n for n,w in EXPORTS.items())
    wires='    wire formal_phase_active,formal_phase_prepared;\n    wire [255:0] formal_program_bits;\n    wire [7:0] formal_sync_meta;\n'
    assignments='\n'+''.join(f'    assign f_{n}={n};\n' for n in EXPORTS)
    top=readouts((src/'project.v').read_text(),[
        ('input wire clk, input wire rst_n\n','input wire clk, input wire rst_n,\n'+ports+'\n'),
        ('    wire engine_rst_n =',wires+'    wire engine_rst_n ='),
        ('    m1_engine engine (','    phase_engine engine ('),
        ('        .instruction_valid(instruction_valid)\n','        .instruction_valid(instruction_valid), .formal_program_bits(formal_program_bits)\n'),
        ('.async_in(uio_in), .sampled_in(sampled_inputs)\n','.async_in(uio_in), .sampled_in(sampled_inputs), .formal_meta(formal_sync_meta)\n'),
        ('        .shift_result_data(shift_result_data)\n','        .shift_result_data(shift_result_data), .formal_phase_active(formal_phase_active), .formal_phase_prepared(formal_phase_prepared)\n'),
        ('\nendmodule',assignments+'\nendmodule')], 'project.v',inputs)
    (inputs/'project.v').write_text(top)
    bindings=''.join('wire '+(f'[{w-1}:0] ' if w>1 else '')+'f_'+n+';\n' for n,w in EXPORTS.items())
    (inputs/'program_bindings.vh').write_text(bindings)
    original=(ROOT/'experiments/spi_phase/pins/public_spi.sv').read_text()
    added='    `include "program_bindings.vh"\n'
    harness=once(original,'    tt_um_khangelani_protocol_emulator dut(.*);',added+'    tt_um_khangelani_protocol_emulator dut(.*);')
    harness=once(harness,'\nendmodule','\n    `include "program_invariants.vh"\nendmodule')
    assert harness.replace(added,'').replace('    `include "program_invariants.vh"\n','')==original
    (inputs/'public_spi.sv').write_text(harness)
    (inputs/'program_invariants.vh').write_bytes((ROOT/'experiments/spi_phase/pins/program_invariants.vh').read_bytes())
    return sources

def preflight(out):
    inputs=out/'inputs'; cases=[]
    for order,tx,rx in ((0,0x96,0x69),(1,0x96,0x69),(0,0,255),(1,255,0)):
        path=out/f'sim-{order}-{tx}-{rx}'; path.mkdir()
        source=(inputs/'public_spi.sv').read_text()
        source=once(source,'(* anyconst *) reg [7:0] tx_byte, rx_byte;',f'reg [7:0] tx_byte=8\'d{tx},rx_byte=8\'d{rx};')
        source=once(source,'(* anyconst *) reg msb_first;',f'reg msb_first=1\'b{order};')
        source=once(source,'(* anyseq *) reg raw_miso, select_valid;', 'reg raw_miso, select_valid;')
        source=once(source,'    tt_um_khangelani_protocol_emulator dut(.*);',
            '    always @(*) begin\n        select_valid=cycle[0]; raw_miso=1;\n        for (integer m=0;m<8;m=m+1)\n            if (exec_edge>=27+50*m) raw_miso=msb_first ? rx_byte[7-m] : rx_byte[m];\n    end\n    tt_um_khangelani_protocol_emulator dut(.*);')
        source=source.replace('assume(','assert(')
        (path/'driver.sv').write_text(source)
        (path/'clock.sv').write_text('`timescale 1ns / 1ps\nmodule sim; reg clk=0; public_spi dut(clk); initial begin repeat(444) begin #10 clk=1; #10 clk=0; end $display("PREFLIGHT_COMPLETE"); $finish; end endmodule\n')
        command=['iverilog','-g2012','-s','sim','-I'+str(inputs),'-o',str(path/'sim.vvp')]
        command += [str(inputs/n) for n in ('project.v','phase_engine.v','m1_program_store.v','m1_data_store.v','m1_input_sync.v')]
        command += [str(path/'driver.sv'),str(path/'clock.sv')]
        with (path/'compile.log').open('w') as log: code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=30).returncode
        if code: raise RuntimeError('preflight compilation failed: '+str(path))
        with (path/'run.log').open('w') as log: code=subprocess.run(['vvp',str(path/'sim.vvp')],stdout=log,stderr=subprocess.STDOUT,timeout=30).returncode
        log=(path/'run.log').read_text()
        ok=code==0 and 'PREFLIGHT_COMPLETE' in log and 'ERROR:' not in log and 'FATAL:' not in log
        cases.append({'order':order,'tx':tx,'rx':rx,'status':'PASS' if ok else 'FAIL','path':str(path.relative_to(out))})
        (out/'preflight.json').write_text(json.dumps(cases,indent=2)+'\n')
        if not ok: raise RuntimeError('preflight assertion failed: '+str(path))
    return cases

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,required=True); p.add_argument('--preflight-only',action='store_true'); args=p.parse_args()
    out=args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT/'build').resolve()): raise ValueError('new isolated build/ directory required')
    sources=prepare(out)
    paths=list((ROOT/'experiments/spi_phase').glob('*.py'))+list((ROOT/'experiments/spi_phase/pins').glob('*'))
    paths += baseline_inputs()+[ROOT/'docs/specs/spi-program-invariant-attempt.md']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in paths if p.is_file()}
    result={'status':'RUNNING','scope':'ACTUAL_PUBLIC_LOADED_EIGHT_WORD_PROGRAM','sources':sources,'input_sha256':hashes,
        'generated_sha256':{p.name:digest(p) for p in (out/'inputs').iterdir()},'proof_budget':{'mode':'prove','depth':12,'wall_seconds':180,'attempts':1},
        'assumptions':'E0024 public driver unchanged; symbolic constant TX/RX/order; raw MISO intended bit only at R=27+50j; select_valid otherwise arbitrary',
        'strengthening':'assertions on actual loaded bytes and complete architectural loop/shift/data state; no added input assumptions'}
    def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        result['preflight']=preflight(out); save(); print('preflight PASS',flush=True)
        if args.preflight_only: result['status']='PREFLIGHT_PASS_NOT_PROOF'; return
        files=['project.v','phase_engine.v','m1_program_store.v','m1_data_store.v','m1_input_sync.v','public_spi.sv','program_bindings.vh','program_invariants.vh']
        cfg='[options]\nmode prove\ndepth 12\n\n[engines]\nsmtbmc z3\n\n[script]\nread -formal -sv '+' '.join(n for n in files if not n.endswith('.vh'))+'\nprep -top public_spi\n\n[files]\n'+'\n'.join(str(out/'inputs'/n) for n in files)+'\n'
        (out/'program.sby').write_text(cfg); command=['sby','-f','-d',str(out/'program'),str(out/'program.sby')]
        start=time.monotonic()
        with (out/'program.log').open('w') as log:
            try: code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
            except subprocess.TimeoutExpired: code=124
        raw=(out/'program/status').read_text().strip() if (out/'program/status').exists() else 'MISSING'
        match=re.fullmatch(r'(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}',raw); status=match.group(1) if match else 'MALFORMED_OR_MISSING'
        log=(out/'program.log').read_text(); induction='successful proof by k-induction' in log
        tried=re.findall(r'Trying induction in step (\d+)',log); checked=re.findall(r'Checking assertions in step (\d+)',log)
        result['proof']={'status':status,'raw_status':raw,'returncode':code,'command':command,'seconds':round(time.monotonic()-start,3),
            'k_induction':induction,'induction_step':int(tried[-1]) if induction else None,
            'last_started_base_step':max(map(int,checked)) if checked else None,
            'failed_assertions':re.findall(r'Assert failed in (.+)',log),
            'witnesses':sorted(str(p.relative_to(out)) for p in (out/'program/engine_0').glob('trace*.vcd'))}
        result['status']='PROVED_WRITTEN_PROGRAM_PROPERTIES' if code==0 and status=='PASS' and induction else 'NOT_PROVED_STOPPED_AT_BUDGET'
        assert hashes=={str(p.relative_to(ROOT)):digest(p) for p in paths if p.is_file()}
        print(result['status'],flush=True)
    except Exception as error: result.update(status='HARNESS_OR_TOOL_FAILURE',error=str(error)); raise
    finally: save(); print(out,flush=True)

if __name__=='__main__': main()
