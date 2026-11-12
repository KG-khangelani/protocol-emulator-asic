# SPDX-License-Identifier: Apache-2.0
"""Bounded digital mode-0 pin experiment; production and candidate stay intact."""

import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
import subprocess
import time
import xml.etree.ElementTree as ET

from build_variants import ROOT,FILES,build
from legacy_baseline import baseline_inputs
from run_formal import digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    parser.add_argument('--formal-only',action='store_true')
    args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=(args.output or ROOT/'build/spi-mode0-pins'/stamp).resolve()
    if out.exists() or not out.is_relative_to((ROOT/'build').resolve()): raise ValueError('new isolated build/ path required')
    sources=build(out/'variants')
    inputs=out/'inputs'; inputs.mkdir()
    for name in ('transport.sv','public_spi.sv'):
        (inputs/name).write_bytes((ROOT/'experiments/spi_phase/pins'/name).read_bytes())
    (inputs/'m1_input_sync.v').write_bytes((out/'variants/compact/src/m1_input_sync.v').read_bytes())
    paths=list((ROOT/'experiments/spi_phase').glob('*.py'))+list((ROOT/'experiments/spi_phase/pins').glob('*.sv'))
    paths += baseline_inputs()
    paths += [ROOT/'test'/n for n in ('Makefile','tb.v','test.py','test_spi_mode0_pins.py')]
    paths += [ROOT/'Makefile',ROOT/'tools/m1_contract_model.py',ROOT/'docs/specs/spi-mode0-pin-qualification.md']
    hashes={str(p.relative_to(ROOT)):digest(p) for p in paths}
    result={'status':'RUNNING','rung':'FULL_PUBLIC_PIN_SIMULATION_AND_INPUT_TRANSPORT_FORMAL',
        'sources':sources,'input_sha256':hashes,'generated_sha256':{p.name:digest(p) for p in inputs.iterdir()},
        'formal_scope':'actual two-stage synchronizer and independent schedule monitor; no executor or loader',
        'assumptions':'initial schedule reset; symbolic constant RX/order; raw MISO constrained only on R=27+50j; other ticks arbitrary',
        'full_program_formal':'INCONCLUSIVE_LOCAL_444_STEP_SAT_TIMEOUTS_NOT_RETRIED_BY_THIS_RUNNER',
        'simulation_envelopes':{'original':'per-bit response5..480ns; setup>=20ns, hold until next launch',
            'digital_stress':'intended bit on closed R+-1ps window; ideal flip-flops; no electrical claim'},
        'tasks':[],'simulations':[]}
    def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        for name,mode,depth,defines,expected in (
            ('transport_prove','prove',8,'','PASS'),('transport_cover','cover',404,'','PASS'),
            ('early_capture','bmc',32,'-D EARLY_CAPTURE','FAIL')):
            config=f'[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\nread -formal -sv {defines} m1_input_sync.v transport.sv\nprep -top transport\n\n[files]\n{inputs/"m1_input_sync.v"}\n{inputs/"transport.sv"}\n'
            (out/(name+'.sby')).write_text(config)
            command=['sby','-f','-d',str(out/name),str(out/(name+'.sby'))]
            start=time.monotonic()
            with (out/(name+'.log')).open('w') as log:
                try: code=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
                except subprocess.TimeoutExpired: code=124
            raw=(out/name/'status').read_text().strip() if (out/name/'status').exists() else 'MISSING'
            match=re.fullmatch(r'(PASS|FAIL|UNKNOWN|ERROR)(?:\s+\d+){0,2}',raw)
            status=match.group(1) if match else 'MALFORMED_OR_MISSING'
            log=(out/(name+'.log')).read_text()
            induction='successful proof by k-induction' in log
            steps=re.findall(r'Trying induction in step (\d+)',log)
            checked=re.findall(r'Checking assertions in step (\d+)',log)
            covers=[{'step':int(n),'location':loc} for n,loc in re.findall(r'Reached cover statement in step (\d+) at (.+)',log)]
            failed=re.findall(r'Assert failed in (.+)',log)
            witnesses=sorted(str(p.relative_to(out)) for p in (out/name/'engine_0').glob('trace*.vcd'))
            task={'name':name,'mode':mode,'depth':depth,'expected':expected,'status':status,'raw_status':raw,
                'returncode':code,'command':command,'seconds':round(time.monotonic()-start,3),
                'k_induction':induction,'induction_step':int(steps[-1]) if induction else None,
                'last_checked_step':max(map(int,checked)) if checked else None,'reached_covers':covers,
                'failed_assertions':failed,'witnesses':witnesses}
            result['tasks'].append(task); save(); print(name,status,'expected',expected,flush=True)
            if code!=0 or status!=expected: raise RuntimeError(f'{name}: {status},exit{code}')
            if mode=='prove' and not induction: raise RuntimeError('missing induction result')
            if mode=='cover' and (len(covers)!=3 or len(witnesses)!=3): raise RuntimeError('missing required covers')
            if expected=='FAIL' and (not failed or not witnesses): raise RuntimeError('missing counterexample')
        if not args.formal_only:
            env=dict(os.environ)
            for key in ('COCOTB_TEST_FILTER','COCOTB_TESTCASE','GATES','MAKEFLAGS'): env.pop(key,None)
            for sim in ('icarus','verilator'):
                directory=out/sim; directory.mkdir()
                env['SPI_PIN_RECORD_DIR']=str(directory/'records')
                command=['make','-C','test','SIM='+sim,'SRC_DIR='+str(out/'variants/compact/src'),
                    'COCOTB_TEST_MODULES=test_spi_mode0_pins','COCOTB_TEST_FILTER=',
                    'SIM_BUILD='+str(directory/'sim'),'COCOTB_RESULTS_FILE='+str(directory/'results.xml'),
                    'FST=','COCOTB_PLUSARGS=+NO_DUMP']
                start=time.monotonic()
                with (out/(sim+'.log')).open('w') as log:
                    code=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
                cases=list(ET.parse(directory/'results.xml').getroot().iter('testcase')) if (directory/'results.xml').exists() else []
                bad=[c.get('name') for c in cases if any(c.find(n) is not None for n in ('failure','error','skipped'))]
                records=[json.loads(line) for line in (directory/'records/cases.jsonl').read_text().splitlines()]
                accepted=[r for r in records if r['accepted']]
                controls=[r for r in records if not r['accepted']]
                ok=code==0 and len(cases)==4 and not bad and len(records)==864 and len(accepted)==856 and len(controls)==8
                ok=ok and len({r['case'] for r in records})==864
                item={'simulator':sim,'status':'PASS' if ok else 'FAIL','returncode':code,'tests':len(cases),
                    'failed_or_skipped':bad,'positive_transactions':len(accepted),'negative_controls':len(controls),
                    'command':command,'seconds':round(time.monotonic()-start,3),
                    'records_sha256':{str(p.relative_to(out)):digest(p) for p in (directory/'records').iterdir()}}
                result['simulations'].append(item); save(); print(sim,item['status'],len(records),'records',flush=True)
                if not ok: raise RuntimeError('pin simulation/manifest failed')
            maps=[{Path(p).name:h for p,h in s['records_sha256'].items()} for s in result['simulations']]
            assert maps[0]==maps[1],'cross-simulator public records differ'
            result['cross_simulator_records']='BYTE_IDENTICAL'
        assert hashes=={str(p.relative_to(ROOT)):digest(p) for p in paths}
        result['status']='PASS'
    except Exception as error:
        result.update(status='FAIL',error=str(error)); raise
    finally: save(); print(out,flush=True)


if __name__=='__main__': main()
