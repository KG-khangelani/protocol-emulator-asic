# SPDX-License-Identifier: Apache-2.0
"""Replay frozen resolution, pin geometry, startup scope and input rejections."""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from types import SimpleNamespace

parser=argparse.ArgumentParser()
parser.add_argument('--directory',type=Path,required=True)
out=parser.parse_args().directory.resolve()
assert out.is_relative_to(Path('/workspace/build'))
read=lambda p:json.loads(p.read_bytes())
assert read(out/'archive-check.json')['status']=='PASS_RETAINED_PORTABLE_ALIGNED_STAGING'
pilot=out/'pilot'
source=pilot/'inputs'
inputs=read(pilot/'inputs.json')
def selected(path,names,space):
    nodes=[]
    for node in ast.parse(path.read_text(encoding='utf-8')).body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            nodes.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):
            nodes.append(node)
    assert len(nodes)==len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),space)
    return space
common=selected(source/'tools/physical_candidate.py',['require','verify_run_configuration','SIGNOFF_CORNERS'],{})
common=SimpleNamespace(**common,candidate_lock=lambda:inputs['flow_lock'])
scope=selected(source/'experiments/i2c/align_sram_magic.py',['ALIGNED_SHA256','MAGIC_TREE_SHA256','NATIVE_DRC_SHA256','REFERENCE_SHA256'],{})
scope.update(common=common,require=common.require,Path=Path,
    digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(),
    MACRO='RM_IHPSG13_1P_256x32_c2_bm_bist',mapped_macro_views=lambda:inputs['macro_views'])
scope=selected(source/'tools/physical_sram.py',['inspect_resolved','portable_config','magic_alignment_contract','MODEL_SETS','TEMPLATE_SHA256','SRAM_IMPORT_PATTERNS','SRAM_IMPORT_SETUP_SHA256'],scope)
gate=SimpleNamespace(**scope)
workspace=pilot/'workspace'
original_workspace='/workspace/build/g2-sram-aligned-staging-01/workspace'
def rebase(value):
    if isinstance(value,str):return value.replace(original_workspace,str(workspace))
    if isinstance(value,list):return [rebase(v) for v in value]
    if isinstance(value,dict):return {k:rebase(v) for k,v in value.items()}
    return value
resolved=rebase(read(workspace/'runs/aligned-pilot/resolved.json'))
resolved['FP_DEF_TEMPLATE']=str(out/'reference/tt_block_8x4_pgvdd.def')
assert gate.inspect_resolved(resolved,inputs,workspace)==inputs['macro_views']
tree=ast.parse((pilot/'pilot-runner.py').read_text(encoding='utf-8'))
starts=[i for i,n in enumerate(tree.body) if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple) and [t.id for t in n.target.elts]==['name','mutate','expected']]
stops=[i for i,n in enumerate(tree.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='grid' for t in n.targets)]
assert len(starts)==len(stops)==1 and starts[0]<stops[0]
space={'controls':[],'gate':gate,'resolved':resolved,'inputs':inputs,'workspace':workspace,'copy':copy,'Path':Path,
       'reference':read(out/'reference/resolved.json')}
exec(compile(ast.Module(body=tree.body[starts[0]:stops[0]],type_ignores=[]),'frozen-aligned-controls','exec'),space)
assert space['controls']==read(pilot/'pilot-verification.json')['controls'] and len(space['controls'])==12
run=workspace/'runs/aligned-pilot'
database=run/'29-odb-applydeftemplate/tt_um_khangelani_protocol_emulator.odb'
subprocess.run(['openroad','-no_init','-exit','-python',str(workspace/'audit_sram_pin_power.py'),
                '--odb',str(database),'--output',str(out/'fresh-pin-audit')],check=True)
assert read(out/'fresh-pin-audit/result.json')==read(run/'30-project-checkpublicpinpower/pin-power-audit/result.json')

def findings(text):
    category,result='',[]
    for line in text.splitlines()[1:]:
        if not line or line.startswith(('-','[INFO]')):continue
        if line.startswith(' '):result.append((category,line.strip()))
        else:category=line
    assert len(result)==int(re.findall(r'\[INFO\] COUNT: (\d+)',text)[-1])
    return sorted(result)
for kind,step in [('proposed','Magic.DRC'),('original','Magic.StreamOut')]:
    work=out/('native-wrapper-'+kind)
    work.mkdir()
    (work/'reports').mkdir()
    text=(out/'wrapper'/kind/'_env.tcl').read_text(encoding='utf-8')
    for key,value in [('STEP_DIR',str(work)),('CURRENT_GDS',str(out/'reference/controls.gds')),('STEP_ID',step)]:
        text,count=re.subn(r'^set ::env\('+key+r'\) .*$','set ::env('+key+') '+value,text,flags=re.M)
        assert count==1
    (work/'_env.tcl').write_bytes(text.encode())
    env=dict(os.environ,_TCL_ENV_IN=str(work/'_env.tcl'),_MAGIC_SCRIPT=str(out/'reference/native/drc.tcl'))
    command=['magic','-dnull','-noconsole','-rcfile',str(workspace/'sram_magicrc.tcl'),str(out/'reference/native/wrapper.tcl')]
    with (work/'run.log').open('wb') as log:
        result=subprocess.run(command,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=60)
    assert result.returncode==0
    assert findings((work/'reports/drc.magic.rpt').read_text())==findings((out/'wrapper'/kind/'reports/drc.magic.rpt').read_text())
    receipt=work/'sram-magic-aligned/alignment.json'
    assert receipt.exists()==(kind=='proposed')
    if kind=='proposed':
        alignment=read(receipt)
        assert alignment['native_drc_script_sha256']==gate.NATIVE_DRC_SHA256
        assert alignment['helper_sha256']==inputs['staged_sha256']['align_sram_magic.py']
        assert alignment['startup_sha256']==inputs['staged_sha256']['sram_magicrc.tcl']
        assert alignment['changed_files']==gate.ALIGNED_SHA256 and alignment['original_tree_sha256']==gate.MAGIC_TREE_SHA256

spec=importlib.util.spec_from_file_location('frozen_aligner',workspace/'align_sram_magic.py')
aligner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(aligner)
pdk=Path(resolved['PDK_ROOT'])/resolved['PDK']
bad=out/'changed-pdk'
shutil.copytree(pdk/'libs.tech/magic',bad/'libs.tech/magic')
for name in aligner.REFERENCE_SHA256:
    if not name.startswith('libs.tech/magic/'):
        path=bad/name
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(pdk/name,path)
changed=bad/'libs.tech/magic/ihp-sg13cmos5l-GDS.tech'
changed.write_bytes(changed.read_bytes()+b'\n# deliberate changed reference\n')
bad_script=out/'changed-native-drc.tcl'
bad_script.write_bytes((out/'reference/native/drc.tcl').read_bytes()+b'\n# deliberate changed full check\n')
rejections=[]
for name,call,expected in (
    ('unguarded_alignment',lambda:gate.portable_config('header.vh',aligned=True),'Magic alignment requires the guarded construction'),
    ('changed_complete_drc_script',lambda:aligner.align(pdk/'libs.tech/magic/ihp-sg13cmos5l.tech',out/'reject-script',bad_script),'original complete DRC script changed'),
    ('changed_other_magic_file',lambda:aligner.align(bad/'libs.tech/magic/ihp-sg13cmos5l.tech',out/'reject-tree',out/'reference/native/drc.tcl'),'pinned Magic source tree changed'),
):
    try:call()
    except ValueError as error:
        assert str(error)==expected
        rejections.append({'fault':name,'rejection':str(error)})
    else:raise AssertionError('missed input rejection: '+name)
assert rejections==read(out/'rejections/result.json')['controls']
assert not (out/'reject-script').exists() and not (out/'reject-tree').exists()
result={'status':'PASS_NATIVE_ALIGNED_STAGING_AND_STARTUP_REPLAY','configuration_controls':space['controls'],
    'input_rejection_controls':rejections,'startup_scope_and_all_contact_findings':'PASS',
    'actual_complete_drc_script_and_magic_tree':'PASS_EXACT_PINNED_IDENTITIES',
    'fresh_actual_pin_geometry':'PASS_43_PINS_ZERO_VIOLATIONS','full_physical_qualification':'OPEN'}
(out/'native-verification.json').write_bytes((json.dumps(result,indent=2)+'\n').encode())
print(result['status'])
