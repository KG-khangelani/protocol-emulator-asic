# SPDX-License-Identifier: Apache-2.0
"""Replay mapped area including the SRAM, exact views and actual connections."""
import argparse
from collections import Counter
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
NAME='RM_IHPSG13_1P_256x32_c2_bm_bist'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda path:json.loads(path.read_bytes())


def normalize(value):
    if isinstance(value,dict):
        return {k:normalize(v) for k,v in value.items()}
    if isinstance(value,list):
        return [normalize(v) for v in value]
    if isinstance(value,str):
        for label in ('gold','sram'):
            value=value.replace('/workspace/build/g2-sram-mapped-01/'+label,'<design>')
    return value


def areas_from(raw):
    text=raw.decode()
    cells=list(re.finditer(r'\bcell\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{',text))
    result={}
    for i,cell in enumerate(cells):
        body=text[cell.end():cells[i+1].start() if i+1<len(cells) else len(text)]
        values=re.findall(r'\barea\s*:\s*([^;]+);',body)
        assert len(values)==1
        result[cell[1]]=Decimal(values[0].strip())
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha((HERE/name).read_bytes())==expected
    index=read(HERE/'archive.json')
    raw=(HERE/'mapping.tar.gz').read_bytes()
    assert sha(raw)==index['sha256'] and len(raw)==index['bytes']
    with tarfile.open(HERE/'mapping.tar.gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(index['files']) and {m.name for m in members}==set(index['files'])
        for member in members:
            path=(out/member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw=archive.extractfile(member).read()
            assert sha(raw)==index['files'][member.name]
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
    run=read(out/'result.json')
    report=read(out/'verification.json')
    assert report==read(HERE/'verification.json') and report['status']=='PASS_MATCHED_SRAM_MAPPED_SCREEN'
    assert run['status']=='MAPPING_COMMANDS_SUCCEEDED_REQUIRES_AUDIT'
    assert run['runner_sha256']==sha((out/'inputs/run_sram_mapping.py').read_bytes())
    assert run['spec_sha256']==sha((out/'inputs/g2-sram-mapped-screen.md').read_bytes())
    runtime=read(out/'runtime-observation.json')
    assert runtime['status']=='OBSERVED_ACTIVE_MAPPING_CONTAINER'
    assert runtime['image_id']==runtime['configured_image']=='sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert len(runtime['pdk_volume_mounts'])==1 and runtime['pdk_volume_mounts'][0]['RW'] is False
    assert runtime['pdk_volume_mounts'][0]['Name']=='protocol-emulator-g1-pdk-89d42ee6'
    candidate=read(HERE.parent/'candidate.json')
    assert run['candidate']==candidate==read(out/'inputs/regression-result.json')['candidate']
    assert read(out/'inputs/regression-result.json')['status']=='PASS_SRAM_CURRENT_BOTH_SIMULATORS'
    assert read(out/'inputs/proof-result.json')['status']=='PASS_SRAM_GATE'
    areas={}
    for name,item in report['libraries'].items():
        raw=gzip.decompress((out/'libraries'/(Path(name).name+'.gz')).read_bytes())
        assert sha(raw)==item['sha256'] and len(raw)==item['bytes']
        current=areas_from(raw)
        assert all(n not in areas or areas[n]==area for n,area in current.items())
        areas.update(current)
    assert areas[NAME]==Decimal('49488.4992')
    model=gzip.decompress((HERE.parent/'feasibility/verilog'/(NAME+'.v.gz')).read_bytes())
    header=model.split(b'// ---- Simulation-only check:')[0].replace(b'module ',b'(* blackbox *) module ')+b'\nendmodule\n`endcelldefine\n'
    assert header==(out/'sram/src'/(NAME+'.vh')).read_bytes()
    configs={}
    for label,count,state,standard in [('gold',34683,4278,Decimal('477788.2578')),('sram',4201,353,Decimal('53089.7598'))]:
        job=run['runs'][label]
        execution=job['execution']
        assert execution['returncode']==0 and not execution['timed_out'] and execution['wall_limit']==300
        assert execution['command'][execution['command'].index('--to')+1]=='Yosys.Synthesis'
        assert {n:sha((out/label/'src'/n).read_bytes()) for n in job['sources']}==job['sources']
        expected=candidate['source_sha256'] if label=='sram' else read(ROOT/'evidence/E0038-shared-program-read/sources/source-manifest.json')['od128']['source_sha256']
        assert job['sources']==expected
        assert sha((out/label/'src/config_merged.json').read_bytes())==job['config_sha256']
        configs[label]=normalize(read(out/label/'runs/mapped-screen/resolved.json'))
        configs[label]['VERILOG_FILES']=sorted(configs[label]['VERILOG_FILES'])
        step=out/label/'runs/mapped-screen/06-yosys-synthesis'
        model=read(step/'tt_um_khangelani_protocol_emulator.nl.v.json')['modules']['tt_um_khangelani_protocol_emulator']
        counts=Counter(c['type'] for c in model['cells'].values())
        measured=report['measurements'][label]
        metrics=read(step/'state_out.json')['metrics']
        assert dict(counts)==measured['cell_types'] and sum(counts.values())==count==metrics['design__instance__count']
        assert metrics==measured['metrics'] and counts['sg13cmos5l_dfrbpq_1']==state==measured['sequential_cells']
        assert sum(areas[n]*v for n,v in counts.items() if n!=NAME)==standard==Decimal(str(metrics['design__instance__area']))
        whole=sum(areas[n]*v for n,v in counts.items())
        assert whole==Decimal(str(measured['complete_mapped_footprint_um2']))
        assert sha((step/'tt_um_khangelani_protocol_emulator.nl.v').read_bytes())==measured['netlist_sha256']
        assert all(metrics[k]==0 for k in ('design__lint_error__count','design__lint_timing_construct__count','design__inferred_latch__count','design__instance_unmapped__count','synthesis__check_error__count'))
        warnings=Counter(re.findall(r'^%Warning-([^:]+):',(out/label/'runs/mapped-screen/01-verilator-lint/verilator-lint.log').read_text(),re.M))
        assert dict(warnings)==measured['lint_warning_types']==({'TIMESCALEMOD':106} if label=='sram' else {'UNUSEDSIGNAL':1})
        if label=='sram':
            assert counts[NAME]==1
            macro=model['cells']['store.program_memory']
            assert macro['type']==NAME
            assert macro['connections']['A_CLK']==model['ports']['clk']['bits']
            assert macro['connections']['A_MEN']==model['ports']['rst_n']['bits']
            constants={'0':0,'1':1}
            for cell in model['cells'].values():
                if cell['type'] in ('sg13cmos5l_tiehi','sg13cmos5l_tielo'):
                    for port,bits in cell['connections'].items():
                        if cell['port_directions'][port]=='output':
                            for bit in bits:
                                assert bit not in constants
                                constants[bit]=int(cell['type']=='sg13cmos5l_tiehi')
            for port,bits in macro['connections'].items():
                if port.startswith('A_BIST'):
                    assert all(constants.get(b)==0 for b in bits)
            assert all(constants.get(b)==1 for port in ('A_DLY','A_REN') for b in macro['connections'][port])
            assert len(macro['connections']['A_DOUT'])==len(set(macro['connections']['A_DOUT']))==32
    diff={k for k in configs['gold']|configs['sram'] if configs['gold'].get(k)!=configs['sram'].get(k)}
    assert diff=={'MACROS'},diff
    assert configs['gold']['CLOCK_PERIOD']==20 and configs['gold']['DIE_AREA']==[0,0,1724.16,710.64]
    assert configs['gold']['OPENROAD_THREADS']==4
    saving=(1-report['measurements']['sram']['complete_mapped_footprint_um2']/report['measurements']['gold']['complete_mapped_footprint_um2'])*100
    assert saving==report['mapped_footprint_reduction_percent'] and saving>=20
    replay={'status':'PASS_RETAINED_MATCHED_SRAM_MAPPING','files':len(index['files']),
            'mapped_footprint_reduction_percent':saving,'configuration_differences':['MACROS'],
            'physical':'NOT_EVALUATED','production':'NOT_PROMOTED'}
    (out/'replay.json').write_bytes((json.dumps(replay,indent=2)+'\n').encode())
    print(json.dumps(replay))


if __name__=='__main__':
    main()
