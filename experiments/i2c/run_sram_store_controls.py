# SPDX-License-Identifier: Apache-2.0
"""Real vendor SRAM model, public store ports and four observed implementation faults."""
import argparse
import json
from pathlib import Path
import re
import sys
from sram_prefetch import ROOT, digest
sys.path.insert(0,str(ROOT/'experiments/spi_phase'))
from run_program_sensitivity import execute


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    candidate,out=args.candidate.resolve(),args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    manifest=json.loads((candidate/'manifest.json').read_bytes())
    original=(candidate/'src/m1_program_store.v').read_bytes()
    assert digest(original)==manifest['source_sha256']['m1_program_store.v']
    models={n:(candidate/'models'/n).read_bytes() for n in manifest['model_sha256']}
    assert {n:digest(raw) for n,raw in models.items()}==manifest['model_sha256']
    bench=(ROOT/'test/sram_program_store.sv').read_bytes()
    mutations={
        'reset-valid-retained':(b"word_valid <= 128'd0;",b'word_valid <= word_valid;','zero_after_reset'),
        'partial-write-stale-lanes':(b"byte_mask : 32'hffffffff;",b'byte_mask : byte_mask;','partial_first_write_zero_padding'),
        'fetch-current-pc':(b': prefetch_pc;',b': pc;','lookahead_fetch'),
        'missing-word-zero-shadow':(b"if (pc == 8'd0)",b"if (1'b0)",'word_zero_after_loader_read'),
    }
    variants={'baseline':original}
    for name,(before,after,_) in mutations.items():
        assert original.count(before)==1
        variants[name]=original.replace(before,after)
    result={'status':'RUNNING','scope':'REAL_VENDOR_FUNCTIONAL_MODEL_STORE_PORTS_ONLY',
            'candidate':manifest,'runner_sha256':digest(Path(__file__).read_bytes()),'bench_sha256':digest(bench),
            'simulation_defines':['FUNCTIONAL','SYNTHESIS'],
            'model_boundary':'SYNTHESIS disables only the vendor A_DLY time-zero monitor; wrapper ties A_DLY high, BIST low. Actual functional memory and write-through model unchanged.',
            'mutations':{n:{'before':a.decode(),'after':b.decode(),'expected_check':c,'sha256':digest(variants[n])} for n,(a,b,c) in mutations.items()},'runs':{}}
    save=lambda:(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    save()
    try:
        for simulator in ('icarus','verilator'):
            result['runs'][simulator]={}
            for name,raw in variants.items():
                work=out/simulator/name
                work.mkdir(parents=True)
                (work/'m1_program_store.v').write_bytes(raw)
                (work/'bench.sv').write_bytes(bench)
                for model,data in models.items():
                    (work/model).write_bytes(data)
                sources=[str(work/'m1_program_store.v'),str(work/'bench.sv'),*(str(work/m) for m in models)]
                executable=work/'simulation'
                if simulator=='icarus':
                    command=['iverilog','-g2012','-DFUNCTIONAL','-DSYNTHESIS','-s','sram_program_store','-o',str(executable),*sources]
                    run_command=['vvp',str(executable)]
                else:
                    command=['verilator','--binary','--timing','-Wno-fatal','-DFUNCTIONAL','-DSYNTHESIS','--top-module','sram_program_store',
                             '--Mdir',str(work/'sim'),'-o',str(executable),*sources]
                    run_command=[str(executable)]
                item={'store_sha256':digest(raw),'compile':execute(command,work/'compile.log',120)}
                result['runs'][simulator][name]=item
                save()
                assert item['compile']['returncode']==0 and not item['compile']['timed_out'],(simulator,name,'compile')
                item['simulation']=execute(run_command,work/'run.log',30)
                log=(work/'run.log').read_text()
                assert not item['simulation']['timed_out']
                if name=='baseline':
                    match=re.search(r'PASS_SRAM_STORE_PORTS checks=(\d+) unknown_checks=(\d+)',log)
                    assert item['simulation']['returncode']==0 and match and 'CHECK_FAILED' not in log
                    checks,unknown=map(int,match.groups())
                    assert checks>=2400 and unknown==(2 if simulator=='icarus' else 0)
                    item.update(status='PASS',checks=checks,unknown_checks=unknown)
                else:
                    witness=re.search(r'^CHECK_FAILED (.+)$',log,re.M)
                    assert item['simulation']['returncode']!=0 and witness and 'STORE_CHECK_FAILED' in log
                    assert 'PASS_SRAM_STORE_PORTS' not in log
                    assert witness[1].split()[0]==mutations[name][2],(simulator,name,witness[1])
                    item.update(status='EXPECTED_OBSERVABLE_FAILURE',witness=witness[1])
                item['log_sha256']=digest((work/'run.log').read_bytes())
                save()
                print(simulator,name,item['status'],flush=True)
        a,b=(result['runs'][sim]['baseline'] for sim in ('icarus','verilator'))
        assert a['checks']-a['unknown_checks']==b['checks']-b['unknown_checks']
        result['status']='PASS_SRAM_STORE_PORTS_AND_FOUR_CHECKED_CONTROLS'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE',error=str(error))
        raise
    finally:
        save()
    print(result['status'],flush=True)


if __name__=='__main__':
    main()
