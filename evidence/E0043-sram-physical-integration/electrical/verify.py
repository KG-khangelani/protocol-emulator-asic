# SPDX-License-Identifier: Apache-2.0
"""Replay rejected routed trials and the two bounded electrical diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
read=lambda p:json.loads(p.read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
IMAGE='sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
CORNERS=('nom_fast_1p32V_m40C','nom_slow_1p08V_125C','nom_typ_1p20V_25C')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',required=True,type=Path)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha((HERE/name).read_bytes())==expected,name
    indices=read(HERE/'archives.json')
    files=0
    for label,index in indices.items():
        packed=(HERE/(label+'.tar.gz')).read_bytes()
        assert len(packed)==index['bytes'] and sha(packed)==index['sha256']
        with tarfile.open(HERE/(label+'.tar.gz')) as archive:
            members=archive.getmembers()
            assert len(members)==len(index['files']) and {m.name for m in members}==set(index['files'])
            for member in members:
                path=(out/label/member.name).resolve()
                assert member.isfile() and path.is_relative_to(out/label)
                raw=archive.extractfile(member).read()
                assert sha(raw)==index['files'][member.name]
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
            files+=len(members)
        runtime=read(out/label/'runtime-observation.json')
        assert runtime['image_id']==IMAGE
        assert len(runtime['pdk_volume_mounts'])==1 and not runtime['pdk_volume_mounts'][0]['RW']
    summaries={};configs=[]
    for label in ('full-01','full-02'):
        base=out/label;run=base/'runs/integrated'
        result=read(base/'run-result.json')
        stop=read(base/'stop-decision.json')
        assert result['status']=='FAILED_OR_INCOMPLETE' and result['execution']['returncode']==-15
        assert not result['execution']['timed_out'] and result['execution']['wall_limit']==10800
        assert stop['status']=='REJECTED_EXTRACTED_SLEW_STOP_REMAINING_CHECKS' and stop['slew_violations']==9
        states=list(run.glob('*-openroad-stapostpnr/state_out.json'));assert len(states)==1
        assert sha(states[0].read_bytes())==stop['state_sha256']
        metrics=read(states[0])['metrics']
        assert metrics['design__max_slew_violation__count']==9
        for corner in CORNERS:
            assert metrics['timing__setup__ws__corner:'+corner]>0 and metrics['timing__hold__ws__corner:'+corner]>0
            for kind in ('fanout','cap'):
                assert metrics[f'design__max_{kind}_violation__count__corner:'+corner]==0
            report=(states[0].parent/corner/'checks.rpt').read_text()
            count=int(re.search(r'max slew violation count (\d+)',report)[1])
            assert count==metrics['design__max_slew_violation__count__corner:'+corner]>0
        slow=(states[0].parent/'nom_slow_1p08V_125C/checks.rpt').read_text()
        rows=re.findall(r'(store\.program_memory/\S+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s+(-\d+\.\d+) \(VIOLATED\)',slow)
        assert len(rows)==9
        assert {r[0] for r in rows}=={*(f'store.program_memory/A_ADDR[{i}]' for i in range(7)),
                                    'store.program_memory/A_WEN','store.program_memory/A_DIN[15]'}
        assert all(float(limit)==0.5952 and float(value)>float(limit) for _,limit,value,_ in rows)
        assert metrics['route__drc_errors']==0
        assert metrics['route__antenna_violation__count']==0 and metrics['design__power_grid_violation__count']==0
        assert not list(run.glob('*-netgen-lvs'))
        prep=read(base/'preparation.json')
        for name,expected in prep['source_sha256'].items(): assert sha((base/'src'/name).read_bytes())==expected
        for name,expected in prep['plugin_sha256'].items(): assert sha((base/name).read_bytes())==expected
        config=(base/'src/config_merged.json').read_bytes()
        assert sha(config)==prep['config_sha256']
        configs.append(json.loads(config.decode().replace('g2-sram-'+label,'NORMALIZED_RUN')))
        summaries[label]={'outcome':'REJECTED_EXTRACTED_SLEW_REMAINING_CHECKS_STOPPED',
                          'slew_violations':9,'minimum_setup_ns':min(metrics['timing__setup__ws__corner:'+c] for c in CORNERS),
                          'minimum_hold_ns':min(metrics['timing__hold__ws__corner:'+c] for c in CORNERS),
                          'elapsed_seconds':result['execution']['seconds']}
    expected=dict(configs[0],RUN_POST_GRT_DESIGN_REPAIR=True)
    assert configs[1]==expected
    first_odb=out/'full-01/runs/integrated/41-openroad-globalrouting/tt_um_khangelani_protocol_emulator.odb'
    for label,seconds in [('transition-screen',20.879),('buffer-screen',16.838)]:
        base=out/label;result=read(base/'result.json')
        assert result['status']=='COMMAND_SUCCEEDED_REQUIRES_ARTIFACT_AUDIT'
        assert result['execution']['returncode']==0 and not result['execution']['timed_out'] and result['execution']['wall_limit']==300
        assert result['execution']['seconds']==seconds
        assert sha(first_odb.read_bytes())==result['input_odb_sha256']
        states=list((base/'runs/screen').glob('*-openroad-stamidpnr-3/state_out.json'));assert len(states)==1
        current=read(states[0])['metrics']['design__max_slew_violation__count__corner:nom_typ_1p20V_25C']
        assert current==(82 if label=='transition-screen' else 0)
        summaries[label]={'seconds':seconds,'fresh_typical_estimated_slew_violations':current,'other_corners':'NOT_FRESHLY_EVALUATED'}
    base=out/'buffer-screen'
    audit=read(base/'connectivity-audit.json')
    assert audit['status']=='PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY' and audit['added_buffers']==9
    assert audit['before_odb_sha256']==sha(first_odb.read_bytes())
    after=base/'runs/screen/01-project-buffersraminputs/tt_um_khangelani_protocol_emulator.odb'
    assert audit['after_odb_sha256']==sha(after.read_bytes())
    controls=read(base/'controls/result.json')
    assert controls['status']=='PASS_BUFFER_AUDITOR_BASELINE_AND_TWO_REAL_WIRING_FAULTS'
    assert controls['auditor_sha256']==sha((base/'controls/auditor.py').read_bytes())
    assert len(controls['runs'])==3
    for row in controls['runs']:
        directory=base/'controls'/row['name']
        assert row['wall_limit']==60 and row['seconds']<60
        assert sha((directory/'run.log').read_bytes())==row['log_sha256']
        if row['name']=='baseline':
            assert row['returncode']==0 and row['database_sha256']==sha(after.read_bytes())
        else:
            assert row['returncode']!=0 and row['database_sha256']==sha((directory/'mutated.odb').read_bytes())
            marker={'crossed-address-loads':'TARGET_NET_IDENTITY_CHANGED','wrong-buffer-input':'BUFFER_INPUT_CHANGED'}[row['name']]
            assert marker in (directory/'run.log').read_text()
    summary={'status':'PASS_RETAINED_ELECTRICAL_REJECTIONS_AND_BOUNDED_SCREENS','files':files,
             'trials':summaries,'connectivity_audit':'PASS_WITH_TWO_CHECKED_WIRING_FAULTS',
             'fast_corner_boundary':'Standard cells at -40 C and SRAM at -55 C, unchanged vendor libraries',
             'physical_qualification':'NOT_QUALIFIED','production':'NOT_PROMOTED'}
    (out/'verification.json').write_bytes((json.dumps(summary,indent=2)+'\n').encode())
    print(json.dumps(summary))


if __name__=='__main__':
    main()
