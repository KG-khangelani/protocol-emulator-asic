# SPDX-License-Identifier: Apache-2.0
"""Replay exact test identities, frozen wire references and bank observations."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda path:json.loads(path.read_bytes())


def selected(path, names, environment):
    chosen=[]
    for node in ast.parse(path.read_text()).body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            chosen.append(node)
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):
            chosen.append(node)
    assert len(chosen)==len(names),(path,names)
    exec(compile(ast.Module(body=chosen,type_ignores=[]),str(path),'exec'),environment)
    return environment


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha((HERE/name).read_bytes())==expected,name
    index=read(HERE/'archive.json')
    packed=(HERE/'regression.tar.gz').read_bytes()
    assert sha(packed)==index['sha256'] and len(packed)==index['bytes']
    with tarfile.open(HERE/'regression.tar.gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(index['files']) and {m.name for m in members}==set(index['files'])
        for member in members:
            path=(out/member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw=archive.extractfile(member).read()
            assert sha(raw)==index['files'][member.name]
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(raw)
    run=out/'run'
    result=read(run/'result.json')
    assert result==read(HERE/'result.json') and result['status']=='PASS_SRAM_CURRENT_BOTH_SIMULATORS'
    candidate=read(HERE.parent/'candidate.json')
    assert result['candidate']==candidate==read(run/'regenerated/manifest.json')
    for name,expected in candidate['source_sha256'].items():
        assert sha((run/'regenerated/src'/name).read_bytes())==expected
    for name,expected in candidate['model_sha256'].items():
        assert sha((run/'regenerated/models'/name).read_bytes())==expected
    for name,expected in result['verification_inputs'].items():
        assert sha((run/'inputs'/name).read_bytes())==expected
    common=selected(run/'inputs/tools/physical_candidate.py',
                    ['PUBLIC_TESTS','PUBLIC_TEST_MODULES','EXCLUDED_TESTS','require'],{})
    checks=selected(run/'inputs/tools/physical_g2.py',
                    ['PUBLIC_TEST_MODULES','records','check_public_records'],
                    {'common':SimpleNamespace(**common),'gzip':gzip,'json':json,
                     'EVIDENCE':out/'references','require':common['require'],
                     'digest':lambda path:sha(path.read_bytes())})
    current=selected(run/'inputs/experiments/i2c/run_current_regression.py',
                     ['REQUIRED','check_junit','check_controls'],
                     {'physical':SimpleNamespace(**checks),'ET':ET})
    assert len(result['stages'])==2 and {s['simulator'] for s in result['stages']}=={'icarus','verilator'}
    observations={}
    for stage in result['stages']:
        simulator=stage['simulator']
        execution=stage['execution']
        assert execution['returncode']==0 and not execution['timed_out'] and execution['wall_limit']==1800
        path=run/simulator
        checked=current['check_junit'](path/'results.xml')
        checked['records']=checks['check_public_records'](path/'records')
        checked['current_bank_control']=current['check_controls'](path/'records/spi/controls.jsonl')
        assert checked==read(path/'check.json')==stage['check']
        log=(path/'run.log').read_text()
        assert ('Running on Icarus Verilog' if simulator=='icarus' else 'Running on Verilator') in log
        assert '-DG2_SRAM' in log and '-DFUNCTIONAL' in log and '-DSYNTHESIS' in log
        observations[simulator]={'groups':checked['test_groups'],'seconds':execution['seconds'],
                                 'records':checked['records'],'bank_observations':checked['current_bank_control']['observations']}
    report={'status':'PASS_RETAINED_SRAM_COMPLETE_PROTOCOL_MATRIX','files':len(index['files']),
            'simulators':observations,'runtime_limit':read(out/'runtime-limit.json'),
            'physical':'NOT_EVALUATED','production':'NOT_PROMOTED'}
    (out/'verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('simulators','runtime_limit')}))


if __name__=='__main__':
    main()
