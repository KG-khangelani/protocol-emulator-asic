"""Audit the original SRAM normal-command CI ZIP and producing container."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
args = parser.parse_args()
base = args.directory.resolve()
assert base.is_relative_to((ROOT / 'build').resolve())
run = read(base / 'run.json')
assert run['status'] == 'completed' and run['conclusion'] == 'success'
assert run['path'] == '.github/workflows/production-current.yaml'
jobs = read(base / 'jobs.json')['jobs']
assert len(jobs) == 1 and jobs[0]['name'] == 'current-production'
job = jobs[0]
assert job['run_id'] == run['id'] and job['run_attempt'] == run['run_attempt']
assert job['status'] == 'completed' and job['conclusion'] == 'success'
artifacts = read(base / 'artifacts.json')['artifacts']
matches = [a for a in artifacts if a['name'] == 'current-production-' + run['head_sha']]
assert len(matches) == 1
metadata = matches[0]
assert metadata['workflow_run']['id'] == run['id']
assert metadata['workflow_run']['head_sha'] == run['head_sha'] and not metadata['expired']
zip_path = base / (str(metadata['id']) + '.zip')
raw = zip_path.read_bytes()
assert len(raw) == metadata['size_in_bytes'] and 'sha256:' + sha(raw) == metadata['digest']
extract = base / 'original'
assert not extract.exists()
zip_hashes = {}
with zipfile.ZipFile(zip_path) as archive:
    entries = archive.infolist()
    assert len(entries) == len({entry.filename for entry in entries}) and archive.testzip() is None
    for entry in entries:
        if entry.is_dir():
            continue
        path = (extract / entry.filename).resolve()
        assert path.is_relative_to(extract)
        content = archive.read(entry)
        zip_hashes[entry.filename] = sha(content)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
pipeline = extract / 'build/current-production'
evidence = read(pipeline / 'evidence.json')
assert evidence['schema'] == 'protocol-emulator-current-evidence-v1' and evidence['status'] == 'PASS'
inputs = base / 'inputs'
for name, expected in evidence['verification_inputs'].items():
    path = (inputs / name).resolve()
    assert path.is_relative_to(inputs) and sha(path.read_bytes()) == expected, name
sys.path.insert(0, str(inputs))
sys.path.insert(0, str(inputs / 'tools'))
from current_run import STAGES, retained_files, semantic_check
from current_profile import describe

profile = describe(inputs / 'src')
assert profile['profile'] == 'od128-sram'
assert evidence['profile'] == profile and set(evidence['stages']) == set(STAGES)
from tools.production_sram import verify as verify_production
production = verify_production(inputs)
assert production == read(pipeline / 'production.json')
assert (extract / 'tools/production-profile.json').read_bytes() == (inputs / 'tools/production-profile.json').read_bytes()
provenance = read(pipeline / 'provenance.json')
assert provenance['status'] == 'PASS' and provenance['profile'] == profile
assert provenance['verification_inputs'] == evidence['verification_inputs']
assert provenance['stages'] == {key: evidence['stages'][key] for key in ('rtl-icarus', 'smoke')}
summaries, runtime = {}, None
for action in STAGES:
    receipt = read(pipeline / 'receipts' / (action + '.json'))
    assert receipt == evidence['stages'][action]
    assert receipt['schema'] == 'protocol-emulator-current-stage-v1' and receipt['status'] == 'PASS'
    assert receipt['action'] == action and receipt['profile'] == profile
    assert receipt['git_head'] == run['head_sha']
    assert receipt['source_directory'] == '/workspace/src', 'normal commands substituted archived candidate sources'
    assert receipt['verification_inputs'] == evidence['verification_inputs']
    relative = PurePosixPath(receipt['directory']).relative_to('build/current-production')
    stage = (pipeline / relative).resolve()
    assert stage.is_relative_to(pipeline)
    assert receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands'])
    assert receipt['artifact_sha256'] == retained_files(stage)
    summaries[action] = semantic_check(action, stage, profile)
    assert summaries[action] == receipt['summary'], action
    assert receipt['artifact_sha256'] == retained_files(stage), 'audit changed retained proof data'
    if action == 'doctor':
        runtime = sha((stage / 'run.log').read_bytes())
        assert 'RESULT: PASS' in (stage / 'run.log').read_text()
    assert receipt['runtime_identity'] == runtime
checks = sorted((pipeline / 'runs').glob('*-check'))
assert len(checks) == 2 and len(list((pipeline / 'runs').iterdir())) == 9
for check in checks:
    log = (check / 'run.log').read_text()
    counts = re.findall(r'^Ran (\d+) tests? in ', log, re.M)
    assert sum(map(int, counts)) == 127
    assert len(re.findall(r'^OK$', log, re.M)) == len(counts)
    assert not re.search(r'^(FAILED|ERROR|FAIL:)', log, re.M)
assert evidence['stages']['check']['directory'].endswith(checks[-1].name)
assert checks[-1].name > max(p.name for p in (pipeline / 'runs').iterdir() if p != checks[-1])
container = read(pipeline / 'runtime/container.json')
images = read(pipeline / 'runtime/workbench-image.json')
assert len(images) == 1
image = images[0]
assert container['image'] == container['configured_image'] == image['Id']
assert container['state']['Status'] == 'exited' and container['state']['ExitCode'] == 0
assert not container['state']['OOMKilled'] and not container['state']['Error']
assert container['command'] == ['sh', '-c',
    'python3 tools/production_sram.py --output build/current-production/production.json && make CURRENT_ARTIFACTS=/workspace/build/current-production doctor check lint test test-verilator formal synth evidence']
assert any(m['Destination'] == '/workspace' and m['RW'] for m in container['mounts'])
joblog = (base / 'current-job.log').read_text(encoding='utf-8-sig')
assert f'Artifact ID {metadata["id"]}' in joblog
assert f'Final size is {metadata["size_in_bytes"]} bytes' in joblog
assert metadata['digest'].removeprefix('sha256:') in joblog and run['head_sha'] in joblog
image_ids = re.findall(r'"containerimage.config.digest": "(sha256:[0-9a-f]{64})"', joblog)
image_manifests = re.findall(r'"containerimage.digest": "(sha256:[0-9a-f]{64})"', joblog)
assert image_ids == [image['Id']] and len(image_manifests) == 1
assert '--name production-current-ci --pull=never' in joblog and '"$current_image"' in joblog
report = {
    'status': 'PASS_DEFAULT_PRODUCTION_COMMAND_CI_ORIGINAL_ARCHIVE', 'run_id': run['id'],
    'source_commit': run['head_sha'], 'job_id': job['id'], 'artifact_id': metadata['id'],
    'original_zip_sha256': sha(raw), 'original_zip_bytes': len(raw), 'original_zip_files': len(zip_hashes),
    'verification_input_files': len(evidence['verification_inputs']), 'profile': profile,
    'runtime_tool_identity': runtime, 'built_image_id': image['Id'], 'built_image_manifest': image_manifests[0],
    'container_exit_code': 0, 'runtime_identity_source': 'Same-job build result, actual container inspect, immutable-image execution and tool report.',
    'stages': summaries, 'metadata_checks': {'executions': 2, 'tests_each': 127, 'collection_reran_fresh': True},
    'physical_qualification': 'SEPARATE_RETAINED_GATE', 'production': production,
}
(base / 'verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
(base / 'zip-files.json').write_bytes((json.dumps(zip_hashes, indent=2) + '\n').encode())
print(report['status'], report['original_zip_files'], report['verification_input_files'])
