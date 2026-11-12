# SPDX-License-Identifier: Apache-2.0
"""Prove every logical word using an arbitrary index and the complete vendor memory."""
import argparse
import json
from pathlib import Path
import re
import sys
from sram_prefetch import ROOT, digest
sys.path.insert(0,str(ROOT/'experiments/spi_phase'))
from run_program_sensitivity import execute, vcd_frames


def once(text,before,after):
    assert text.count(before)==1,(before,text.count(before))
    return text.replace(before,after)


def instrument(store,models,properties):
    changes=[]
    def edit(name,text,before,after):
        changed=once(text,before,after)
        changes.append({'file':name,'before':before,'after':after})
        return changed
    core='RM_IHPSG13_1P_core_behavioral_bm_bist.v'
    macro='RM_IHPSG13_1P_256x32_c2_bm_bist.v'
    result=dict(models)
    text=result[core].decode()
    text=edit(core,text,'A_BIST_CLK\n                                );','A_BIST_CLK, F_ADDR, F_WORD\n                                );')
    text=edit(core,text,'endmodule','input wire [P_ADDR_WIDTH-1:0] F_ADDR;\noutput wire [P_DATA_WIDTH-1:0] F_WORD;\nassign F_WORD = memory[F_ADDR];\nendmodule')
    result[core]=text.encode()
    text=result[macro].decode()
    text=edit(macro,text,'    A_BIST_BM\n);','    A_BIST_BM, F_ADDR, F_WORD\n);')
    text=edit(macro,text,'    input A_CLK;','    input wire [7:0] F_ADDR;\n    output wire [31:0] F_WORD;\n    input A_CLK;')
    # Only the FUNCTIONAL branch is compiled. Keep the inactive timing branch exact.
    before='                    .A_BIST_BM(A_BIST_BM)'
    assert text.count(before)==1
    text=edit(macro,text,before,before+', .F_ADDR(F_ADDR), .F_WORD(F_WORD)')
    result[macro]=text.encode()
    text=store.decode()
    text=edit('m1_program_store.v',text,'.A_BIST_DIN(32\'d0), .A_BIST_BM(32\'d0)',
              '.A_BIST_DIN(32\'d0), .A_BIST_BM(32\'d0), .F_ADDR({1\'b0, f_index}), .F_WORD(f_physical_word)')
    text=edit('m1_program_store.v',text,'endmodule',properties.decode()+'\nendmodule')
    result['m1_program_store.v']=text.encode()
    return result,changes


def inspect_mutant(task):
    observations=[]
    for path in sorted((task/'proof/engine_0').glob('trace*.vcd')):
        raw=path.read_text()
        normalized=once(raw,'$scope module m1_program_store $end','$scope module public_spi $end')
        target=task/('parsed-'+path.name)
        target.write_bytes(normalized.encode())
        rows=[r for r in vcd_frames(target) if r['time']%10==0]
        for a,b in zip(rows,rows[1:]):
            if (a.get('rst_n') and a.get('f_byte_write') and a.get('f_program_address')==a.get('f_index')
                    and b.get('f_physical_word') is not None and b.get('f_expected') is not None
                    and b['f_physical_word']!=b['f_expected']):
                lane=a['byte_address']%4
                mask=255 << (8*lane)
                assert b['f_expected'] & mask == a['data_in'] << (8*lane)
                assert b['f_physical_word'] & mask == b['f_expected'] & mask
                assert (b['f_physical_word'] ^ b['f_expected']) & ~mask
                observations.append({k:b[k] for k in ('time','f_index','f_physical_word','f_expected')})
    assert observations,'negative proof must show stale physical lanes after a real byte write'
    return observations


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    candidate,out=args.candidate.resolve(),args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    (out/'inputs').mkdir(parents=True)
    manifest=json.loads((candidate/'manifest.json').read_bytes())
    store=(candidate/'src/m1_program_store.v').read_bytes()
    models={n:(candidate/'models'/n).read_bytes() for n in manifest['model_sha256']}
    assert digest(store)==manifest['source_sha256']['m1_program_store.v']
    assert {n:digest(raw) for n,raw in models.items()}==manifest['model_sha256']
    properties=(ROOT/'experiments/i2c/sram_store_properties.vh').read_bytes()
    instrumented,changes=instrument(store,models,properties)
    for path in (Path(__file__),ROOT/'experiments/i2c/sram_store_properties.vh',ROOT/'experiments/spi_phase/run_program_sensitivity.py'):
        (out/'inputs'/path.name).write_bytes(path.read_bytes())
    for name,raw in {**models,'m1_program_store.v':store}.items():
        (out/'inputs'/name).write_bytes(raw)
    result={'status':'RUNNING','scope':'ARBITRARY_LOGICAL_WORD_WITH_COMPLETE_VENDOR_SRAM_MODEL',
            'runner_sha256':digest(Path(__file__).read_bytes()),'candidate':manifest,'properties_sha256':digest(properties),
            'instrumentation':changes,'assumptions':['first sampled edge reset','arbitrary constant 7-bit logical word index; all functional inputs unrestricted'],
            'trusted_boundary':'Exact vendor digital SRAM model; added ports only observe a selected physical word. No array replacement, initialization or clock/write/read change.',
            'tasks':[]}
    save=lambda:(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    save()
    try:
        for name,mode,depth,expected in [('logical-store','prove',5,'PASS'),('covers','cover',10,'PASS'),('partial-mask','bmc',8,'FAIL')]:
            task=out/name
            task.mkdir()
            sources=dict(instrumented)
            if mode=='bmc':
                sources['m1_program_store.v']=once(sources['m1_program_store.v'].decode(),"byte_mask : 32'hffffffff;",'byte_mask : byte_mask;').encode()
            for source,raw in sources.items():
                (task/source).write_bytes(raw)
            config=f'[options]\nmode {mode}\ndepth {depth}\nexpect {expected.lower()}\n\n[engines]\nsmtbmc z3\n\n[script]\n'
            config+='read -formal -sv -D FUNCTIONAL -D SYNTHESIS '+' '.join(sources)+'\n'
            config+='prep -top m1_program_store -flatten\n\n[files]\n'+'\n'.join(str(task/n) for n in sources)+'\n'
            (task/'proof.sby').write_bytes(config.encode())
            stage=execute(['sby','-f','-d',str(task/'proof'),str(task/'proof.sby')],task/'run.log',300)
            status=(task/'proof/status').read_text().split()[0] if (task/'proof/status').exists() else 'MISSING'
            log=(task/'run.log').read_text()
            witnesses={p.relative_to(task).as_posix():digest(p.read_bytes()) for p in (task/'proof/engine_0').glob('trace*.vcd')}
            accepted=stage['returncode']==0 and not stage['timed_out'] and status==expected
            item={'name':name,'mode':mode,'depth':depth,'expected':expected,'status':status,'stage':stage,
                  'source_sha256':{n:digest(raw) for n,raw in sources.items()},'witnesses':witnesses,'accepted':accepted}
            if mode=='prove':
                item['induction']='successful proof by k-induction' in log
                item['accepted'] &= item['induction']
            else:
                item['accepted'] &= bool(witnesses)
            result['tasks'].append(item)
            save()
            assert item['accepted'],(name,status)
            if mode=='bmc':
                item['observed_counterexample']=inspect_mutant(task)
                save()
            print(name,status,'ACCEPTED',flush=True)
        result['status']='PASS_ARBITRARY_LOGICAL_STORE_AND_REAL_MODEL_CONTROL'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE',error=str(error))
        raise
    finally:
        save()
    print(result['status'],flush=True)


if __name__=='__main__':
    main()
