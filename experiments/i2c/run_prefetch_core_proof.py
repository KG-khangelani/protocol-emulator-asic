# SPDX-License-Identifier: Apache-2.0
"""Compare every real engine state/output under arbitrary input sequences."""
import argparse
import json
from pathlib import Path
import re
import sys
from sram_prefetch import ROOT, digest, parent_sources, engine_with_next_pc
sys.path.insert(0,str(ROOT/'experiments/spi_phase'))
from run_program_sensitivity import execute

read=lambda p:json.loads(p.read_bytes())


def audit_models(models):
    states,ports,all_names={},{},set()
    for label,module in models.items():
        assert not any('latch' in c['type'].lower() or c['type'] in ('$assume','$anyseq','$anyconst') for c in module['cells'].values())
        q={b for c in module['cells'].values() if 'dff' in c['type'].lower() for b in c['connections']['Q'] if isinstance(b,int)}
        assert len(q)==128
        names={n:w['bits'] for n,w in module['netnames'].items() if not n.startswith('$')}
        states[label]={n:bits for n,bits in names.items() if any(b in q for b in bits) and all(not isinstance(b,int) or b in q for b in bits)}
        ports[label]={n:(p['direction'],len(p['bits'])) for n,p in module['ports'].items()}
        all_names |= set(names)
    assert ports['gold']==ports['gate'] and 'prefetch_pc' not in ports['gate']
    assert sum(width for direction,width in ports['gold'].values() if direction=='output')==128
    common=set(states['gold'])&set(states['gate'])
    for label,module in models.items():
        q={b for c in module['cells'].values() if 'dff' in c['type'].lower() for b in c['connections']['Q'] if isinstance(b,int)}
        assert q <= {b for n in common for b in states[label][n]}
    return sorted(common),sorted(all_names-common-set(ports['gold']))


def audit_comparisons(before,after,common):
    comparisons={n:c for n,c in before['cells'].items() if c['type']=='$equiv'}
    output_bits={b for p in before['ports'].values() if p['direction']=='output' for b in p['bits']}
    assert output_bits <= {b for c in comparisons.values() for b in c['connections']['Y']}
    pairs={(c['connections']['A'][0],c['connections']['B'][0]) for c in comparisons.values()}
    for name in common:
        a,b=(before['netnames'][name+suffix]['bits'] for suffix in ('_gold','_gate'))
        assert len(a)==len(b) and all((x,y) in pairs or (y,x) in pairs for x,y in zip(a,b)),name
    assert all(after['cells'][n]['connections']['A']==after['cells'][n]['connections']['B'] for n in comparisons)
    return len(comparisons)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    (out/'inputs').mkdir(parents=True)
    for path in (Path(__file__),ROOT/'experiments/i2c/sram_prefetch.py',ROOT/'docs/specs/g2-sram-prefetch-screen.md'):
        (out/'inputs'/path.name).write_bytes(path.read_bytes())
    parent=parent_sources()
    gate,transformation=engine_with_next_pc(parent['m1_engine.v'])
    source=parent['m1_engine.v'].decode()
    declaration=source[:source.index('\n);')+4]
    port_names=re.findall(r'\b(?:input|output)\s+(?:wire|reg)\s*(?:\[[^\]]+\]\s*)?([A-Za-z_]\w*)',declaration)
    assert len(port_names)==len(set(port_names))
    wrapper=declaration.replace('module m1_engine #','module engine_boundary #')+'\n'
    wrapper+='m1_engine #(.COMPACT_PHASE(COMPACT_PHASE)) engine ('+', '.join('.'+n+'('+n+')' for n in port_names)+');\nendmodule\n'
    (out/'boundary.v').write_bytes(wrapper.encode())
    result={'status':'RUNNING','scope':'COMPOSITIONAL_ENGINE_EQUIVALENCE_WITH_BYTE_IDENTICAL_SURROUNDINGS',
            'runner_sha256':digest(Path(__file__).read_bytes()),'builder_sha256':digest((out/'inputs/sram_prefetch.py').read_bytes()),
            'spec_sha256':digest((out/'inputs/g2-sram-prefetch-screen.md').read_bytes()),
            'transformation':transformation,'stages':{},'unchanged_surrounding_sources':{n:digest(raw) for n,raw in parent.items() if n!='m1_engine.v'},
            'engine_sources':{'gold':digest(parent['m1_engine.v']),'gate':digest(gate)},
            'limits':'Original engine interface only. New prefetch output and SRAM require separate integration proof/tests; both earlier full-chip attempts timed out.'}
    save=lambda:(out/'result.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
    save()
    def run(label,script,limit):
        (out/(label+'.ys')).write_bytes((script+'\n').encode())
        stage=execute(['yosys','-Q','-s',str(out/(label+'.ys'))],out/(label+'.log'),limit)
        result['stages'][label]=stage
        save()
        assert stage['returncode']==0 and not stage['timed_out'],label
    try:
        models={}
        for label,raw in [('gold',parent['m1_engine.v']),('gate',gate)]:
            path=out/(label+'.v')
            path.write_bytes(raw)
            script=f'read_verilog {path} {out/"boundary.v"}; hierarchy -check -top engine_boundary; proc; flatten; opt; '
            script+=f'check -assert; rename engine_boundary {label}; write_rtlil {out/(label+".il")}; write_json {out/(label+".json")}'
            run(label,script,60)
            models[label]=read(out/(label+'.json'))['modules'][label]
        common,excluded=audit_models(models)
        result.update(actual_state_bits=128,original_output_bits=128,common_state_names=common,excluded_combinational_names=excluded)
        (out/'blacklist.txt').write_bytes(('\n'.join(excluded)+'\n').encode())
        inputs=f'read_rtlil {out/"gold.il"} {out/"gate.il"}; '
        script=inputs+f'equiv_make -blacklist {out/"blacklist.txt"} gold gate equivalence; hierarchy -top equivalence; '
        script+=f'write_json {out/"before.json"}; equiv_induct -seq 1; equiv_simple; equiv_status -assert; write_json {out/"after.json"}'
        run('temporal',script,120)
        assert 'Equivalence successfully proven!' in (out/'temporal.log').read_text()
        count=audit_comparisons(read(out/'before.json')['modules']['equivalence'],read(out/'after.json')['modules']['equivalence'],common)
        result['proven_bit_comparisons_including_aliases']=count
        script=inputs+f'equiv_make -make_assert -blacklist {out/"blacklist.txt"} gold gate equivalence; hierarchy -top equivalence; '
        script+=f'dffunmap; opt_clean; write_json {out/"reset.json"}; sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports'
        run('reset',script,60)
        assert 'SAT proof finished - no model found: SUCCESS!' in (out/'reset.log').read_text()
        model=read(out/'reset.json')['modules']['equivalence']
        assertions=[c for c in model['cells'].values() if c['type']=='$assert']
        eq=[c for c in model['cells'].values() if c['type']=='$eqx']
        assert not any(c['type']=='$assume' for c in model['cells'].values())
        assert all(c['connections']['EN']==['1'] for c in assertions)
        assert {tuple(c['connections']['A']) for c in assertions}=={tuple(c['connections']['Y']) for c in eq}
        pairs={(tuple(c['connections']['A']),tuple(c['connections']['B'])) for c in eq}
        for name in common+[n for n,p in model['ports'].items() if p['direction']=='output']:
            a,b=(tuple(model['netnames'][name+suffix]['bits']) for suffix in ('_gold','_gate'))
            assert (a,b) in pairs or (b,a) in pairs,name
        assert sum(int(c['parameters']['A_WIDTH'],2) for c in eq)==count
        result['reset_base']={'vector_assertions':len(assertions),'compared_bits_including_aliases':count}
        result['model_sha256']={n:digest((out/n).read_bytes()) for n in ('gold.il','gate.il','gold.json','gate.json','before.json','after.json','reset.json','blacklist.txt')}
        result['status']='PASS_COMPOSITIONAL_NEXT_STATE_ENGINE_EQUIVALENCE'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE',error=str(error))
        raise
    finally:
        save()
    print(result['status'],flush=True)


if __name__=='__main__':
    main()
