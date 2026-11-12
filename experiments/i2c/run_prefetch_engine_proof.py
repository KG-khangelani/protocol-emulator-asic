# SPDX-License-Identifier: Apache-2.0
"""Prove the next-state engine refactor on the complete unchanged D39 chip."""
import argparse
import json
from pathlib import Path
import sys

from sram_prefetch import ROOT, digest, parent_sources, engine_with_next_pc
from run_shared_read_proof import state_matches, check_temporal, check_reset
sys.path.insert(0,str(ROOT/'experiments/spi_phase'))
from run_program_sensitivity import execute

TOP='tt_um_khangelani_protocol_emulator'
read=lambda p:json.loads(p.read_bytes())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--induction-first',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    gold=parent_sources()
    result={'status':'RUNNING','scope':'COMPLETE_D39_CHIP_WITH_ONLY_ENGINE_NEXT_STATE_REFACTOR',
            'runner_sha256':digest(Path(__file__).read_bytes()),
            'builder_sha256':digest((ROOT/'experiments/i2c/sram_prefetch.py').read_bytes()),
            'spec_sha256':digest((ROOT/'docs/specs/g2-sram-prefetch-screen.md').read_bytes()),
            'proof_order':'induction-first' if args.induction_first else 'simple-first','stages':{}}
    (out/'inputs').mkdir()
    for path in (Path(__file__),ROOT/'experiments/i2c/sram_prefetch.py',ROOT/'experiments/i2c/run_shared_read_proof.py',ROOT/'docs/specs/g2-sram-prefetch-screen.md'):
        (out/'inputs'/path.name).write_bytes(path.read_bytes())
    save=lambda:(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    save()
    def run(label,script,limit):
        path=out/(label+'.ys')
        path.write_bytes((script+'\n').encode())
        stage=execute(['yosys','-Q','-s',str(path)],out/(label+'.log'),limit)
        result['stages'][label]=stage
        save()
        assert stage['returncode']==0 and not stage['timed_out'],label
    try:
        gate=dict(gold)
        gate['m1_engine.v'],transformation=engine_with_next_pc(gold['m1_engine.v'])
        result['transformation']=transformation
        result['sources']={label:{n:digest(raw) for n,raw in sources.items()} for label,sources in [('gold',gold),('gate',gate)]}
        models={}
        for label,sources in [('gold',gold),('gate',gate)]:
            directory=out/label/'src'
            directory.mkdir(parents=True)
            for name,raw in sources.items():
                (directory/name).write_bytes(raw)
            script='read_verilog '+ ' '.join(str(directory/name) for name in sources)
            script+=f'; hierarchy -check -top {TOP}; proc; flatten; opt; check -assert; rename {TOP} {label}; '
            script+=f'write_rtlil {out/(label+".il")}; write_json {out/(label+".json")}'
            run(label,script,60)
            models[label]=read(out/(label+'.json'))['modules'][label]
        common,excluded=state_matches(models)
        (out/'blacklist.txt').write_bytes(('\n'.join(excluded)+'\n').encode())
        result.update(actual_state_bits_per_chip=4278,common_state_names=common,excluded_combinational_names=excluded)
        inputs=f'read_rtlil {out/"gold.il"} {out/"gate.il"}; '
        script=inputs+f'equiv_make -blacklist {out/"blacklist.txt"} gold gate equivalence; hierarchy -top equivalence; '
        schedule='equiv_induct -seq 1; equiv_simple' if args.induction_first else 'equiv_simple; equiv_induct -seq 1'
        script+=f'write_json {out/"before.json"}; {schedule}; equiv_status -assert; write_json {out/"after.json"}'
        run('temporal',script,120)
        assert 'Equivalence successfully proven!' in (out/'temporal.log').read_text()
        count=check_temporal(read(out/'before.json')['modules']['equivalence'],read(out/'after.json')['modules']['equivalence'],common)
        result.update(public_output_bits=24,proven_bit_comparisons_including_aliases=count,temporal_maximum_step=1)
        script=inputs+f'equiv_make -make_assert -blacklist {out/"blacklist.txt"} gold gate equivalence; '
        script+=f'hierarchy -top equivalence; dffunmap; opt_clean; write_json {out/"reset.json"}; '
        script+='sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports'
        run('reset',script,60)
        assert 'SAT proof finished - no model found: SUCCESS!' in (out/'reset.log').read_text()
        result['reset_base']=check_reset(read(out/'reset.json')['modules']['equivalence'],common,count)
        result['model_sha256']={n:digest((out/n).read_bytes()) for n in ('gold.il','gate.il','gold.json','gate.json','before.json','after.json','reset.json','blacklist.txt')}
        result['status']='PASS_COMPLETE_CHIP_NEXT_STATE_REFACTOR'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE',error=str(error))
        raise
    finally:
        save()
    print(result['status'],flush=True)


if __name__=='__main__':
    main()
