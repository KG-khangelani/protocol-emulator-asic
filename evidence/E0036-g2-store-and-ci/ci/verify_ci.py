import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools import physical_candidate as physical
BASE=ROOT/'build/g2-ci-31ebf82'
OUT=ROOT/'evidence/E0036-g2-store-and-ci/ci'
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p: json.loads(p.read_text())
rows=lambda p: [json.loads(s) for s in p.read_text().splitlines()]
expected=read(ROOT/'evidence/E0035-general-i2c/sources/current/source-manifest.json')
metadata=read(BASE/'artifacts.json')['artifacts']
verified=[]
for artifact in metadata:
    if not artifact['name'].startswith('i2c-general-'):
        continue
    number=artifact['id']
    assert artifact['workflow_run']['head_sha']=='31ebf8247fab05f2e6e23bc94e1d861562f0f1b5'
    assert 'sha256:'+sha(BASE/f'{number}.zip')==artifact['digest']
    data=BASE/str(number)
    name='architecture' if number==13943422095 else 'od128' if number==13943266477 else 'literal255'
    variants=data/('variants' if name=='architecture' else 'protocols/variants')
    assert read(variants/'source-manifest.json')==expected
    for variant,item in expected.items():
        for file,digest in item['source_sha256'].items():
            assert sha(variants/variant/'src'/file)==digest
    result=read(data/('result.json' if name=='architecture' else 'protocols/result.json'))
    if name!='architecture':
        assert result['status']=='PASS_I2C_PUBLIC_MATRIX' and not result['smoke']
        assert result['parent_revision']==artifact['workflow_run']['head_sha']
        assert result['public_records_per_simulator']==1160 and result['positives']==1154
        a,b=[rows(data/f'protocols/{sim}/records/cases.jsonl') for sim in ('icarus','verilator')]
        assert a==b and len(a)==1160 and sum(r['accepted'] for r in a)==1154
        for stage in result['stages']:
            assert stage['status']=='PASS' and stage['returncode']==0 and stage['observed_identity']
        for file,digest in result['input_sha256'].items():
            frozen=subprocess.check_output(['git','show',f"{artifact['workflow_run']['head_sha']}:{file}"],cwd=ROOT)
            assert hashlib.sha256(frozen).hexdigest()==digest, file
    else:
        assert result['status']=='PASS_SCOPED_ARCHITECTURE_GATE'
        statuses={'boundaries':'PASS_PUBLIC_BOUNDARIES','aborts':'PASS_PUBLIC_ABORT_AND_RELOAD',
          'formal':'PASS_SCOPED_INSTRUCTION_PROOFS','cost':'PASS_GENERIC_COST_ONLY','combined':'PASS_LEGACY_PUBLIC_MATRIX'}
        for sub,status in statuses.items():
            assert read(data/sub/'result.json')['status']==status
        for variant in expected:
            for sub in ('boundaries','cost'):
                assert read(data/sub/'result.json')['sources'][variant]==expected[variant]['source_sha256']
            assert read(data/'formal/result.json')['sources'][variant]==expected[variant]['source_sha256']['m1_engine.v']
            a,b=[rows(data/f'boundaries/{variant}-{sim}/records/boundaries.jsonl') for sim in ('icarus','verilator')]
            assert a==b and len(a)==4
        a,b=[rows(data/f'aborts/od128-{sim}/records/aborts.jsonl') for sim in ('icarus','verilator')]
        assert a==b and len(a)==36 and all(not r['errors'] for r in a)
        for sim in ('icarus','verilator'):
            physical.check_tests(SimpleNamespace(variant='compact10',junit=data/f'combined/{sim}/results.xml',
                records=data/f'combined/{sim}/records/cases.jsonl', output=BASE/f'{sim}-combined-audit.json',require_netlist=False))
    destination=OUT/name
    for file in data.rglob('*'):
        if not file.is_file():
            continue
        relative=file.relative_to(data)
        # Generated RTL already has durable exact copies in E0035. Preserve observations and execution logs.
        if file.name not in ('result.json','results.xml','run.log','synthesis.log') and 'records' not in relative.parts:
            continue
        if 'records' in relative.parts and file.suffix == '.json':
            continue
        target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        if file.suffix in ('.jsonl','.log') or file.name!='result.json' and file.suffix=='.json':
            target=target.with_name(target.name+'.gz')
            target.write_bytes(gzip.compress(file.read_bytes(),mtime=0))
        else:
            shutil.copyfile(file,target)
    for directory in data.rglob('records'):
        witnesses=sorted(directory.glob('*.json'))
        if not witnesses:
            continue
        packed=io.BytesIO()
        with tarfile.open(fileobj=packed,mode='w') as archive:
            for file in witnesses:
                entry=tarfile.TarInfo(file.name)
                body=file.read_bytes()
                entry.size=len(body)
                entry.mtime=0
                archive.addfile(entry,io.BytesIO(body))
        target=destination/directory.relative_to(data)/'witnesses.tar.gz'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress(packed.getvalue(),mtime=0))
        with tarfile.open(fileobj=io.BytesIO(gzip.decompress(target.read_bytes()))) as archive:
            for file in witnesses:
                assert archive.extractfile(file.name).read()==file.read_bytes()
    verified.append(dict(artifact_id=number,name=artifact['name'],zip_sha256=sha(BASE/f'{number}.zip'),
        size=artifact['size_in_bytes'],source_sha256=expected,status=result['status']))
assert len(verified)==3
report=dict(status='PASS_AUDITED_G2_CI',workflow_run=43213815994,
    revision='31ebf8247fab05f2e6e23bc94e1d861562f0f1b5',artifacts=verified,
    scope='Full I2C for both candidates, boundaries, od128 aborts/combined protocols, instruction proofs and generic cost',
    limitations='Store proofs are a separate gate; no physical or production qualification')
(OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
shutil.copyfile(BASE/'artifacts.json',OUT/'artifacts.json')
print('PASS: audited three exact-commit CI archives and retained their observations')
