# SPDX-License-Identifier: Apache-2.0
"""Actual compact top/loader/store/synchronizer qualification in isolated copies."""

import argparse
from datetime import datetime, timezone
import difflib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from build_variants import ROOT, FILES, build, once
from run_formal import PORTS, DERIVED, INPUTS, digest, instrument, vector


def readouts(source, changes, label, output):
    original = source
    for old, new in changes:
        source = once(source, old, new)
    restored = source
    for old, new in reversed(changes):
        restored = once(restored, new, old)
    assert restored == original
    patch = ''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True),
                                        fromfile='compact/'+label, tofile='formal/'+label))
    (output/(label+'.patch')).write_text(patch)
    return source


def prepare(output):
    sources = build(output/'variants')
    src = output/'variants/compact/src'
    inputs = output/'inputs'
    inputs.mkdir()
    (inputs/'phase_engine.v').write_text(instrument((src/'m1_engine.v').read_text()))
    state_names = [n for n in PORTS if n not in DERIVED]
    states = state_names+['formal_phase_active','formal_phase_prepared']
    widths = [PORTS[n] for n in state_names]+[1,1]
    declarations = []
    for name in INPUTS:
        width = 32 if name == 'instruction' else (8 if name in ('sampled_inputs','tx_payload','tx_payload_alt') else 1)
        declarations.append('input wire '+(f'[{width-1}:0] ' if width>1 else '')+name)
    for name,width in PORTS.items():
        declarations.append('input wire '+(f'[{width-1}:0] ' if width>1 else '')+name)
    declarations += ['input wire formal_phase_active','input wire formal_phase_prepared']
    original_observer = (ROOT/'experiments/spi_phase/formal/phase_properties.sv').read_text()
    body = original_observer.split('    `include "phase_bindings.vh"',1)[1].rsplit('endmodule',1)[0]
    body = once(body, '        if (!past_valid) assume(!rst_n);\n', '')
    assert sum('cover(' in line for line in body.splitlines()) == 10
    body = '\n'.join(line for line in body.splitlines() if 'cover(' not in line)+'\n'
    assert 'assume(' not in body
    observer = '/* SPDX-License-Identifier: Apache-2.0 */\n`default_nettype none\nmodule phase_observer(\n'+',\n'.join(declarations)+'\n);\n'
    observer += vector('all_state',states,widths)
    latched = [n for n in state_names if n not in {'pc','state','wait_left'}]
    observer += vector('phase_latched_state',latched+states[-2:],[PORTS[n] for n in latched]+[1,1])
    observer += body+'endmodule\n`default_nettype wire\n'
    (inputs/'phase_observer.sv').write_text(observer)
    store = readouts((src/'m1_program_store.v').read_text(),[
        ('    output wire instruction_valid\n','    output wire instruction_valid, output wire [255:0] formal_program_bits\n'),
        ('    reg [31:0] word4, word5, word6, word7;',
         '    reg [31:0] word4, word5, word6, word7;\n    assign formal_program_bits = {word7,word6,word5,word4,word3,word2,word1,word0};')], 'm1_program_store.v',inputs)
    (inputs/'m1_program_store.v').write_text(store)
    sync = readouts((src/'m1_input_sync.v').read_text(),[
        ('    output reg [7:0] sampled_in\n','    output reg [7:0] sampled_in, output wire [7:0] formal_meta\n'),
        ('    reg [7:0] metastability_stage;', '    reg [7:0] metastability_stage;\n    assign formal_meta = metastability_stage;')], 'm1_input_sync.v',inputs)
    (inputs/'m1_input_sync.v').write_text(sync)
    (inputs/'m1_data_store.v').write_bytes((src/'m1_data_store.v').read_bytes())
    observer_ports = [f'.{n}('+('engine_rst_n' if n=='rst_n' else n)+')' for n in INPUTS]
    observer_ports += [f'.{n}({n})' for n in PORTS]
    observer_ports += ['.formal_phase_active(formal_phase_active)','.formal_phase_prepared(formal_phase_prepared)']
    extra = '\n    phase_observer actual_engine_observer('+',\n'.join(observer_ports)+');\n'
    extra += '    `include "integration_properties.vh"\n'
    taps = '    wire formal_phase_active, formal_phase_prepared;\n    wire [255:0] formal_program_bits;\n    wire [7:0] formal_sync_meta;\n'
    taps += '    '+vector('integrated_engine_state',states,widths)
    project = readouts((src/'project.v').read_text(),[
        ('    wire engine_rst_n =',taps+'    wire engine_rst_n ='),
        ('    m1_engine engine (','    phase_engine engine ('),
        ('        .instruction_valid(instruction_valid)\n','        .instruction_valid(instruction_valid), .formal_program_bits(formal_program_bits)\n'),
        ('.async_in(uio_in), .sampled_in(sampled_inputs)\n','.async_in(uio_in), .sampled_in(sampled_inputs), .formal_meta(formal_sync_meta)\n'),
        ('        .shift_result_data(shift_result_data)\n','        .shift_result_data(shift_result_data),\n        .formal_phase_active(formal_phase_active), .formal_phase_prepared(formal_phase_prepared)\n'),
        ('\nendmodule',extra+'\nendmodule')], 'project.v',inputs)
    (inputs/'project.v').write_text(project)
    dropped = once(project,'.data_in(uio_in), .shift_result_write(shift_result_write),',
                    '.data_in(uio_in), .shift_result_write(1\'b0),')
    (inputs/'project_drop.v').write_text(dropped)
    for name in ('integration_properties.vh','public_scenario.sv'):
        (inputs/name).write_bytes((ROOT/'experiments/spi_phase/formal'/name).read_bytes())
    return sources


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path)
    p.add_argument('--with-simulation',action='store_true')
    p.add_argument('--tasks',nargs='+',default=['integrated_prove','capture_bmc','abort_bmc','capture_cover','abort_cover','wrong_abort_clear','dropped_capture'])
    args=p.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=(args.output or ROOT/'build/spi-phase-integration'/stamp).resolve()
    if output.exists() or not output.is_relative_to((ROOT/'build').resolve()):
        raise ValueError('new isolated build/ output required')
    sources=prepare(output)
    paths=list((ROOT/'experiments/spi_phase').glob('*.py'))+list((ROOT/'experiments/spi_phase/formal').glob('*'))
    paths += [ROOT/'src'/n for n in FILES]+[ROOT/'docs/specs/spi-phase-integration.md']
    paths += [ROOT/'test'/n for n in ('Makefile','tb.v','test.py','test_uart_rx_public.py',
                                    'test_spi_mode0_public.py','test_phase_integration_public.py')]
    hashes={str(x.relative_to(ROOT)):digest(x) for x in paths if x.is_file()}
    record={'status':'RUNNING','rung':'ACTUAL_COMPACT_TOP_INTEGRATION','sources':sources,
            'input_sha256':hashes,'generated_sha256':{str(x.relative_to(output)):digest(x) for x in (output/'inputs').iterdir()},
            'assumptions':{'universal':'initial sampled chip reset only; public pins/enable/reset thereafter arbitrary',
                           'guided':'public serialized four-word kernel; symbolic TX/RX/order; formal abort at capture-edge41,kind0..2,enable0/1; simulation covers cuts2..41',
                           'fairness':'none'},'tasks':[],'simulations':[]}
    config={
        'integrated_prove':('prove',8,'tt_um_khangelani_protocol_emulator','','project.v','PASS',0),
        'capture_bmc':('bmc',80,'public_scenario','','project.v','PASS',0),
        'abort_bmc':('bmc',72,'public_scenario','-D ABORT_SCENARIO','project.v','PASS',0),
        'capture_cover':('cover',80,'public_scenario','','project.v','PASS',4),
        'abort_cover':('cover',72,'public_scenario','-D ABORT_SCENARIO','project.v','PASS',4),
        'wrong_abort_clear':('bmc',80,'public_scenario','-D EXPECT_ABORT_CLEAR','project.v','FAIL',0),
        'dropped_capture':('bmc',80,'public_scenario','','project_drop.v','FAIL',0)}
    def save(): (output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    save()
    try:
        for name in args.tasks:
            mode,depth,top,defines,project,expected,cover_count=config[name]
            files=['phase_engine.v','m1_program_store.v','m1_data_store.v','m1_input_sync.v','phase_observer.sv',project,'integration_properties.vh','public_scenario.sv']
            verilog=[n for n in files if not n.endswith('.vh')]
            script='read -formal -sv '+defines+' '+' '.join(verilog)+'\nprep -top '+top
            sby=f'[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n{script}\n\n[files]\n'+'\n'.join(str(output/'inputs'/n) for n in files)+'\n'
            (output/(name+'.sby')).write_text(sby)
            command=['sby','-f','-d',str(output/name),str(output/(name+'.sby'))]
            started=time.monotonic()
            with (output/(name+'.log')).open('w') as log:
                try: code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=300).returncode
                except subprocess.TimeoutExpired: code=124
            status_file=output/name/'status'
            raw=status_file.read_text().strip() if status_file.exists() else 'MISSING'
            match=re.fullmatch(r'(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}',raw)
            status=match.group(1) if match else 'MALFORMED_OR_MISSING'
            log=(output/(name+'.log')).read_text()
            induction='successful proof by k-induction' in log
            attempts=re.findall(r'Trying induction in step (\d+)',log)
            checked=re.findall(r'Checking assertions in step (\d+)',log)
            reached=[{'step':int(s),'location':loc} for s,loc in re.findall(r'Reached cover statement in step (\d+) at (.+)',log)]
            failed=re.findall(r'Assert failed in (.+)',log)
            witnesses=sorted(str(x.relative_to(output)) for x in (output/name/'engine_0').glob('trace*.vcd'))
            item={'name':name,'mode':mode,'depth':depth,'top':top,'defines':defines,'expected':expected,'status':status,'raw_status':raw,
                  'returncode':code,'command':command,'seconds':round(time.monotonic()-started,3),'k_induction':induction,
                  'induction_step':int(attempts[-1]) if induction else None,'last_checked_step':max(map(int,checked)) if checked else None,
                  'reached_covers':reached,'failed_assertions':failed,'witnesses':witnesses}
            record['tasks'].append(item); save(); print(name,status,'expected',expected,flush=True)
            if code!=0 or status!=expected: raise RuntimeError(f'{name}: {status},exit{code}; retained logs/witnesses')
            if mode=='prove' and not induction: raise RuntimeError('missing induction result')
            if mode=='cover' and (len(reached)!=cover_count or not witnesses): raise RuntimeError('missing cover obligations/witnesses')
            if expected=='FAIL' and (not failed or not witnesses): raise RuntimeError('missing falsification witness')
        if args.with_simulation:
            env=dict(os.environ)
            for key in ('COCOTB_TEST_FILTER','COCOTB_TESTCASE','GATES','MAKEFLAGS'):
                env.pop(key,None)
            for simulator in ('icarus','verilator'):
                junit=output/(simulator+'.xml')
                command=['make','-C','test','SIM='+simulator,
                         'SRC_DIR='+str(output/'variants/compact/src'),
                         'COCOTB_TEST_MODULES=test_phase_integration_public',
                         'COCOTB_TEST_FILTER=', 'SIM_BUILD='+str(output/'sim'/simulator),
                         'COCOTB_RESULTS_FILE='+str(junit),'FST=','COCOTB_PLUSARGS=+NO_DUMP']
                started=time.monotonic()
                with (output/(simulator+'.log')).open('w') as log:
                    code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300).returncode
                cases=list(ET.parse(junit).getroot().iter('testcase')) if junit.exists() else []
                failed=[x.attrib.get('name') for x in cases if any(x.find(n) is not None for n in ('failure','error','skipped'))]
                ok=code==0 and len(cases)==4 and not failed
                record['simulations'].append({'simulator':simulator,'status':'PASS' if ok else 'FAIL',
                    'returncode':code,'tests':len(cases),'failed_or_skipped':failed,'command':command,
                    'seconds':round(time.monotonic()-started,3),'junit':junit.name})
                save(); print(simulator,'PASS' if ok else 'FAIL',flush=True)
                if not ok: raise RuntimeError('public integration simulation failed; inspect retained log/JUnit')
        assert hashes=={str(x.relative_to(ROOT)):digest(x) for x in paths if x.is_file()}
        record['status']='PASS'
    except Exception as error:
        record.update(status='FAIL',error=str(error)); raise
    finally:
        save(); print(output,flush=True)


if __name__=='__main__': main()
