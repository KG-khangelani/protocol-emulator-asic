# SPDX-License-Identifier: Apache-2.0
"""E0042 semantic proof checks, applied to the original CI files."""
import ast, hashlib, json, re
read=lambda p:json.loads(p.read_bytes())
digest=lambda b:hashlib.sha256(b).hexdigest()

def functions(path,names,environment=None):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    chosen=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in chosen}==set(names)
    space={'digest':digest,'re':re,**(environment or {})}
    exec(compile(ast.Module(body=chosen,type_ignores=[]),str(path),'exec'),space)
    return space


def check(out, candidate, old):
    core=read(out/'engine/result.json')
    assert core['status']=='PASS_COMPOSITIONAL_NEXT_STATE_ENGINE_EQUIVALENCE'
    assert all(s['returncode']==0 and not s['timed_out'] for s in core['stages'].values())
    for name,sha in core['model_sha256'].items():
        assert digest((out/'engine'/name).read_bytes())==sha
    assert digest((out/'engine/inputs/run_prefetch_core_proof.py').read_bytes())==core['runner_sha256']
    assert digest((out/'engine/inputs/sram_prefetch.py').read_bytes())==core['builder_sha256']
    assert digest((out/'engine/inputs/g2-sram-prefetch-screen.md').read_bytes())==core['spec_sha256']
    builder=functions(out/'engine/inputs/sram_prefetch.py',['engine_with_next_pc'])
    transformed,change=builder['engine_with_next_pc']((out/'engine/gold.v').read_bytes())
    assert transformed==(out/'engine/gate.v').read_bytes()==(out/'candidate/src/m1_engine.v').read_bytes()
    assert change==core['transformation']
    models={label:read(out/'engine'/(label+'.json'))['modules'][label] for label in ('gold','gate')}
    audit=functions(out/'engine/inputs/run_prefetch_core_proof.py',['audit_models','audit_comparisons'])
    common,excluded=audit['audit_models'](models)
    assert common==core['common_state_names'] and excluded==core['excluded_combinational_names']
    count=audit['audit_comparisons'](read(out/'engine/before.json')['modules']['equivalence'],read(out/'engine/after.json')['modules']['equivalence'],common)
    assert count==core['proven_bit_comparisons_including_aliases']==331
    assert 'Equivalence successfully proven!' in (out/'engine/temporal.log').read_text()
    reset=read(out/'engine/reset.json')['modules']['equivalence']
    assertions=[c for c in reset['cells'].values() if c['type']=='$assert']
    pairs=[c for c in reset['cells'].values() if c['type']=='$eqx']
    assert len(assertions)==69 and all(c['connections']['EN']==['1'] for c in assertions)
    assert not any(c['type']=='$assume' for c in reset['cells'].values())
    assert sum(int(c['parameters']['A_WIDTH'],2) for c in pairs)==count
    assert {tuple(c['connections']['Y']) for c in pairs}=={tuple(c['connections']['A']) for c in assertions}
    connections={(tuple(c['connections']['A']),tuple(c['connections']['B'])) for c in pairs}
    for name in common+[n for n,port in reset['ports'].items() if port['direction']=='output']:
        a,b=(tuple(reset['netnames'][name+suffix]['bits']) for suffix in ('_gold','_gate'))
        assert (a,b) in connections or (b,a) in connections
    assert 'SAT proof finished - no model found: SUCCESS!' in (out/'engine/reset.log').read_text()
    assert core['engine_sources']['gold']==old['m1_engine.v']
    assert core['unchanged_surrounding_sources']=={n:s for n,s in old.items() if n!='m1_engine.v'}
    controls=read(out/'store-controls/result.json')
    assert controls['status']=='PASS_SRAM_STORE_PORTS_AND_FOUR_CHECKED_CONTROLS'
    assert controls['candidate']==candidate
    assert digest((out/'inputs/experiments/i2c/run_sram_store_controls.py').read_bytes())==controls['runner_sha256']
    assert digest((out/'inputs/test/sram_program_store.sv').read_bytes())==controls['bench_sha256']
    for simulator,runs in controls['runs'].items():
        assert set(runs)=={'baseline',*controls['mutations']}
        for name,item in runs.items():
            path=out/'store-controls'/simulator/name
            assert item['compile']['returncode']==0 and not item['compile']['timed_out'] and not item['simulation']['timed_out']
            assert digest((path/'m1_program_store.v').read_bytes())==item['store_sha256']
            assert digest((path/'run.log').read_bytes())==item['log_sha256']
            log=(path/'run.log').read_text()
            if name=='baseline':
                assert item['simulation']['returncode']==0 and item['checks']==(2462 if simulator=='icarus' else 2460)
                assert 'PASS_SRAM_STORE_PORTS' in log and 'CHECK_FAILED' not in log
            else:
                mutation=controls['mutations'][name]
                assert item['simulation']['returncode']!=0 and 'STORE_CHECK_FAILED' in log
                assert 'CHECK_FAILED '+item['witness'] in log and item['witness'].split()[0]==mutation['expected_check']
                assert controls['candidate']['source_sha256']['m1_program_store.v']==digest((out/'candidate/src/m1_program_store.v').read_bytes())
                assert (out/'candidate/src/m1_program_store.v').read_bytes().replace(mutation['before'].encode(),mutation['after'].encode())==(path/'m1_program_store.v').read_bytes()
    formal=read(out/'store-formal/result.json')
    assert formal['status']=='PASS_ARBITRARY_LOGICAL_STORE_AND_REAL_MODEL_CONTROL'
    assert formal['candidate']==candidate
    helper=functions(out/'store-formal/inputs/run_sram_store_formal.py',['once','instrument'])
    original={name:(out/'candidate/models'/name).read_bytes() for name in candidate['model_sha256']}
    properties=(out/'store-formal/inputs/sram_store_properties.vh').read_bytes()
    assert digest(properties)==formal['properties_sha256']
    instrumented,changes=helper['instrument']((out/'candidate/src/m1_program_store.v').read_bytes(),original,properties)
    assert changes==formal['instrumentation']
    parser=functions(out/'store-formal/inputs/run_program_sensitivity.py',['vcd_frames'])['vcd_frames']
    cover_rows=[]
    for task in formal['tasks']:
        path=out/'store-formal'/task['name']
        assert task['accepted'] and task['stage']['returncode']==0 and not task['stage']['timed_out']
        assert (path/'proof/status').read_text().split()[0]==task['expected']
        for name,sha in task['source_sha256'].items():
            raw=(path/name).read_bytes()
            assert digest(raw)==sha
            wanted=instrumented[name]
            if task['mode']=='bmc' and name=='m1_program_store.v':
                wanted=wanted.replace(b"byte_mask : 32'hffffffff;",b'byte_mask : byte_mask;')
            assert raw==wanted
        design=read(path/'proof/model/design.json')['modules']
        assert len(design)==1
        sorts={item['type']:item['cells'] for item in design[0]['cell_sorts']}
        assert len(sorts['$mem_v2'])==1
        memory=sorts['$mem_v2'][0]['parameters']
        assert int(memory['SIZE'],2)==256 and int(memory['WIDTH'],2)==32 and set(memory['INIT'])=={'x'}
        assert len(sorts['$anyconst'])==1 and int(sorts['$anyconst'][0]['parameters']['WIDTH'],2)==7
        flavors=[c['parameters']['FLAVOR'] for c in sorts['$check']]
        assert flavors.count('assert')==18 and flavors.count('assume')==1 and flavors.count('cover')==4
        assert 'connect \\WR_CLK \\clk' in (path/'proof/model/design.il').read_text()
        if task['mode']=='prove':
            assert 'successful proof by k-induction' in (path/'run.log').read_text()
        for name,sha in task['witnesses'].items():
            witness=path/name
            assert digest(witness.read_bytes())==sha
            normalized=witness.read_text().replace('$scope module m1_program_store $end','$scope module public_spi $end')
            # Write only a newly extracted parsing copy, never the retained witness.
            parsed=path/('replay-'+witness.name)
            parsed.write_bytes(normalized.encode())
            rows=[r for r in parser(parsed) if r['time']%10==0]
            if task['mode']=='cover':
                cover_rows.extend(rows)
            else:
                observations=[]
                for a,b in zip(rows,rows[1:]):
                    if a.get('rst_n') and a.get('f_byte_write') and a.get('f_program_address')==a.get('f_index') and b.get('f_physical_word')!=b.get('f_expected'):
                        mask=255 << (8*(a['byte_address']%4))
                        assert b['f_expected'] & mask==a['data_in'] << (8*(a['byte_address']%4))
                        assert b['f_physical_word'] & mask==b['f_expected'] & mask
                        assert (b['f_physical_word']^b['f_expected']) & ~mask
                        observations.append({k:b[k] for k in ('time','f_index','f_physical_word','f_expected')})
                assert observations==task['observed_counterexample'] and observations
    assert any(r.get('f_reset_seen') and r.get('f_index')==127 and r.get('program_ready') and r.get('program_length')==128 and r.get('pc')==127 and r.get('instruction_valid') and r.get('instruction') for r in cover_rows)
    assert any(r.get('f_reset_seen') and r.get('f_index')==0 and r.get('word_zero',0)>>24 and r.get('instruction_valid') and r.get('pc')==0 for r in cover_rows)
    assert any(r.get('f_reset_seen') and r.get('f_seen_write') and not (r.get('word_valid',0)>>r.get('f_index',0))&1 and r.get('f_physical_word') and r.get('f_expected')==0 for r in cover_rows)
    assert any(r.get('f_reset_seen') and r.get('ena')==0 and r.get('read_address')==r.get('f_index') and r.get('read_word') for r in cover_rows)
    return {'engine_compared_bits':331,'engine_reset_vectors':69,'store_assertions':18,'covers':4,'faults_per_simulator':4}
