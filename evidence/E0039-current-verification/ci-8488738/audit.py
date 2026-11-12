import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, default=Path('build/g2-ci-current-8488738'))
args = parser.parse_args()
BASE = args.directory.resolve()
INPUTS = BASE / 'inputs'
PIPELINE = BASE / 'pipeline'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
sys.path.insert(0, str(INPUTS / 'tools'))
sys.path.insert(0, str(INPUTS))
from current_run import STAGES, retained_files, semantic_check
from current_profile import describe

evidence = read(PIPELINE / 'evidence.json')
profile = describe(INPUTS / 'evidence/E0038-shared-program-read/sources/od128')
assert evidence['schema'] == 'protocol-emulator-current-evidence-v1' and evidence['status'] == 'PASS'
assert evidence['profile'] == profile and set(evidence['stages']) == set(STAGES)
assert {p.relative_to(INPUTS).as_posix(): sha(p) for p in INPUTS.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts} == evidence['verification_inputs']
jobs = read(BASE / 'jobs.json')['jobs']
assert {j['name'] for j in jobs} == {'test','learning-windows','current-candidate'}
assert all(j['run_id'] == 43267588725 and j['status'] == 'completed' and j['conclusion'] == 'success' for j in jobs)
assert next(j for j in jobs if j['name'] == 'current-candidate')['id'] == 131371975025
artifact = next(a for a in read(BASE/'artifacts.json')['artifacts'] if a['id'] == 13971730764)
assert artifact['workflow_run']['head_sha'] == '848873898c9b02947b414a6c9211738a93b7c829'
assert artifact['workflow_run']['id'] == 43267588725 and not artifact['expired']
assert artifact['digest'] == 'sha256:804dd04cbaad570b2a92d4ecb0411743a887a547297695272da3be90483e6610'
provenance = read(PIPELINE / 'provenance.json')
assert provenance['status'] == 'PASS' and provenance['profile'] == profile
assert provenance['verification_inputs'] == evidence['verification_inputs']
assert provenance['stages'] == {key:evidence['stages'][key] for key in ('rtl-icarus','smoke')}
summaries, runtime = {}, None
for action in STAGES:
    receipt = read(PIPELINE / 'receipts' / (action + '.json'))
    assert receipt == evidence['stages'][action]
    assert receipt['schema'] == 'protocol-emulator-current-stage-v1' and receipt['status'] == 'PASS'
    assert receipt['action'] == action and receipt['profile'] == profile
    assert receipt['git_head'] == artifact['workflow_run']['head_sha']
    assert receipt['verification_inputs'] == evidence['verification_inputs']
    relative = PurePosixPath(receipt['directory']).relative_to('build/current-candidate')
    stage = (PIPELINE / relative).resolve()
    assert stage.is_relative_to(PIPELINE)
    assert receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands'])
    assert receipt['artifact_sha256'] == retained_files(stage)
    summary = semantic_check(action, stage, profile)
    assert summary == receipt['summary'], action
    assert receipt['artifact_sha256'] == retained_files(stage)
    if action == 'doctor':
        runtime = sha(stage / 'run.log')
        assert 'RESULT: PASS' in (stage / 'run.log').read_text(encoding='utf-8')
    assert receipt['runtime_identity'] == runtime
    summaries[action] = summary

# Collection reruns the metadata checks, rather than accepting the early receipt.
checks = sorted((PIPELINE / 'runs').glob('*-check'))
assert len(checks) == 2 and len(list((PIPELINE / 'runs').iterdir())) == 9
for check in checks:
    log = (check / 'run.log').read_text()
    counts = re.findall(r'^Ran (\d+) tests? in ',log,re.M)
    assert sum(map(int,counts)) == 114
    assert len(re.findall(r'^OK$',log,re.M)) == len(counts)
    assert not re.search(r'^(FAILED|ERROR|FAIL:)',log,re.M)
assert evidence['stages']['check']['directory'].endswith(checks[-1].name)
assert checks[-1].name > max(p.name for p in (PIPELINE/'runs').iterdir() if p != checks[-1])
joblog = (BASE/'current-job.log').read_text(encoding='utf-8-sig')
assert 'Artifact ID 13971730764' in joblog and 'Final size is 6959083 bytes' in joblog
assert artifact['digest'].removeprefix('sha256:') in joblog
assert artifact['workflow_run']['head_sha'] in joblog
image_id = re.findall(r'"containerimage.config.digest": "(sha256:[0-9a-f]{64})"', joblog)
image_manifest = re.findall(r'"containerimage.digest": "(sha256:[0-9a-f]{64})"', joblog)
assert image_id == ['sha256:cc26d9e866b6dd1b3612a8c6d8e50c31cc962b9ccea4c91c66a83a88eb173b36']
assert image_manifest == ['sha256:a42d40adf960b437ba02214c28cab1bdec905e26a23782470a8306946f23b2b8']
assert '--tag protocol-emulator-asic-workbench:2026-07-29 --load' in joblog
assert 'Run docker run --rm --pull=never' in joblog
assert '--workdir /workspace protocol-emulator-asic-workbench:2026-07-29' in joblog
formal_dir = PIPELINE / PurePosixPath(evidence['stages']['formal']['directory']).relative_to('build/current-candidate')
temporal = read(formal_dir / 'current/chip/result.json')['stages']['temporal']
assert temporal['returncode'] == 0 and not temporal['timed_out'] and temporal['wall_limit'] == 300
report = {'status':'PASS_CURRENT_COMMAND_CI_ARCHIVE','source_commit':artifact['workflow_run']['head_sha'],
          'run_id':43267588725,'job_id':131371975025,'artifact_id':13971730764,
          'original_zip_sha256':artifact['digest'].removeprefix('sha256:'),'original_zip_bytes':6959083,
          'profile':profile,'verification_input_files':len(evidence['verification_inputs']),
          'runtime_tool_identity':runtime,'built_image_id':image_id[0],
          'built_image_manifest':image_manifest[0],'runtime_identity_source':'CI build output and same-job --pull=never command; exact in-container tool report',
          'stages':summaries,
          'metadata_checks':{'executions':2,'tests_each':114,'collection_reran_fresh':True},
          'current_temporal_proof':temporal,
          'physical_qualification':'NOT_EVALUATED','production':'NOT_PROMOTED'}
(BASE/'verification.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k not in ('stages','profile')}))
