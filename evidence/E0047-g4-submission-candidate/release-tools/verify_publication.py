# SPDX-License-Identifier: Apache-2.0
"""Audit original publication CI, anonymous release downloads and exact registry identity."""
import argparse
import ast
import concurrent.futures
from datetime import datetime, timezone
import gzip
import importlib.util
import io
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPO = 'KG-khangelani/protocol-emulator-asic'
TAG = 'v0.1.0'
PHYSICAL_SOURCE = '45c55f7cd95db2a883b0ffb5e864decd62d53601'
PHYSICAL_RUNS = {'candidate': 43543626249, 'reproduction': 43543629839}
parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--assets', type=Path, help='Prepared G4 assets; defaults to build/g4-release-assets/<release-source>')
args = parser.parse_args()
base = args.directory.resolve()
assert base.is_relative_to((ROOT / 'build').resolve())
assert sys.platform.startswith('linux'), 'Use the pinned Linux workbench for the original waveform parser.'
read = lambda path: json.loads(path.read_bytes())
raw_sha = lambda raw: hashlib.sha256(raw).hexdigest()

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def write(path, value):
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())

run = read(base / 'run.json')
assert run['status'] == 'completed' and run['conclusion'] == 'success'
assert run['path'] == '.github/workflows/publish.yaml' and run['event'] == 'push'
assert run['head_branch'] == TAG
SOURCE = run['head_sha']
jobs = read(base / 'jobs.json')['jobs']
assert len(jobs) == 1 and jobs[0]['name'] == 'workbench'
job = jobs[0]
assert job['run_id'] == run['id'] and job['run_attempt'] == run['run_attempt']
assert job['head_sha'] == SOURCE
assert job['status'] == 'completed' and job['conclusion'] == 'success'
assert all(step['conclusion'] == 'success' for step in job['steps'])
# Refuse an incomplete release before unpacking or downloading any assets.
tag_records = read(base / 'tag-workflows.json')
tag_runs = tag_records['runs']
expected_workflows = {'test', 'docs', 'atlas', 'i2c-general', 'sram-candidate',
                      'spi-program-sensitivity', 'spi-timed-gpio', 'program-tools', 'publish'}
assert len(tag_runs) == len(expected_workflows) and {r['name'] for r in tag_runs} == expected_workflows
tag_jobs = {}
for tagged in tag_runs:
    assert tagged['head_sha'] == SOURCE and tagged['head_branch'] == TAG and tagged['event'] == 'push'
    assert tagged['status'] == 'completed' and tagged['conclusion'] == 'success'
    items = tag_records['jobs'][str(tagged['id'])]['jobs']
    assert items and all(j['run_id'] == tagged['id'] and j['run_attempt'] == tagged['run_attempt']
                         and j['head_sha'] == SOURCE for j in items)
    assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in items)
    assert all(s['conclusion'] in ('success', 'skipped') for j in items for s in j['steps'])
    tag_jobs[tagged['name']] = {'run_id': tagged['id'], 'jobs': {j['name']: j['id'] for j in items},
                               'conclusion': 'success'}
assert tag_jobs['publish']['run_id'] == run['id']

release = read(base / 'release.json')
assert release['tag_name'] == TAG and release['prerelease'] is False and release['draft'] is False
tag = read(base / 'tag-commit.json')
assert tag['type'] == 'commit' and tag['sha'] == SOURCE
tag_ref, tag_object = read(base / 'tag-ref.json'), read(base / 'tag-object.json')
assert tag_ref['ref'] == 'refs/tags/' + TAG and tag_ref['object']['type'] == 'tag'
assert tag_ref['object']['sha'] == tag_object['sha'] and tag_object['tag'] == TAG
assert tag_object['object'] == tag
assert release['body'].replace('\r\n', '\n').strip().startswith(git('show', SOURCE + ':docs/releases/' + TAG + '.md').decode().strip())
artifacts = read(base / 'artifacts.json')['artifacts']
matches = [a for a in artifacts if a['name'] == 'publication-' + SOURCE]
assert len(matches) == 1
meta = matches[0]
assert meta['workflow_run']['id'] == run['id'] and meta['workflow_run']['head_sha'] == SOURCE and not meta['expired']
original = base / (str(meta['id']) + '.zip')
assert original.stat().st_size == meta['size_in_bytes'] and 'sha256:' + sha(original) == meta['digest']
ci = base / 'original'
assert not ci.exists()
zip_members = {}
with zipfile.ZipFile(original) as archive:
    entries = archive.infolist()
    assert len(entries) == len({e.filename for e in entries}) and archive.testzip() is None
    for entry in entries:
        if entry.is_dir():
            continue
        path = (ci / entry.filename).resolve()
        assert path.is_relative_to(ci)
        raw = archive.read(entry)
        zip_members[entry.filename] = raw_sha(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
write(base / 'zip-files.json', zip_members)
pubdirs = list(ci.rglob('publication.json'))
assert len(pubdirs) == 1
pubdir = pubdirs[0].parent
local = args.assets.resolve() if args.assets else ROOT / 'build/g4-release-assets' / SOURCE
assert local.is_relative_to((ROOT / 'build').resolve())
g4 = read(local / 'g4-submission.json')
assert g4['schema'] == 'protocol-emulator-g4-release-package-v1'
assert g4['release_source_commit'] == SOURCE and g4['tag'] == TAG
assert g4['target'] == 'od128-sram-v1' and g4['interface_id'] == '0x22'
g3 = g4['g3']
frozen = ROOT / 'evidence/E0046-program-toolchain/ci-0297655'
for name, expected in g4['frozen_evidence_members_sha256'].items():
    if name.startswith('evidence/E0046-program-toolchain/ci-0297655/'):
        assert sha(ROOT / name) == expected == raw_sha(git('show', SOURCE + ':' + name)), name
for name in ('14022181491.zip', '14022515054.zip'):
    assert sha(frozen / name) == raw_sha(git('show', SOURCE + ':evidence/E0046-program-toolchain/ci-0297655/' + name))
spec = importlib.util.spec_from_file_location('g3_frozen_audit', frozen / 'verify.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
checked = audit.audit(frozen)
assert checked == read(frozen / 'verification.json')
assert g3['verification_record'] == 'evidence/E0046-program-toolchain/ci-0297655/verification.json'
assert sha(frozen / 'verification.json') == g3['verification_record_sha256']
public = audit.zip_files(frozen / '14022181491.zip')
windows = audit.zip_files(frozen / '14022515054.zip')
assert g3['qualification_source_commit'] == audit.SOURCE and g3['run_id'] == audit.RUN
historical_inputs = json.loads(public['result.json'])['inputs_sha256']
assert historical_inputs == g3['inputs_sha256']
assert len(historical_inputs) == g3['verification_inputs_unchanged'] == 351
pipeline = ci / 'build/current'
evidence = read(pipeline / 'evidence.json')
index = {'files': evidence['verification_inputs']}
assert historical_inputs.items() <= index['files'].items(), 'qualified G3 verification inputs changed'
# Derive full membership from the release Git tree using the unchanged producer's
# literal input-selection contract, not merely the self-reported CI file count.
profile_raw = git('show', SOURCE + ':tools/current_profile.py')
assert raw_sha(profile_raw) == historical_inputs['tools/current_profile.py']
function = next(n for n in ast.parse(profile_raw).body if isinstance(n, ast.FunctionDef) and n.name == 'verification_inputs')
constants = {n.targets[0].id: ast.literal_eval(n.value) for n in function.body
             if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
             and n.targets[0].id in ('prefixes', 'singles')}
assert set(constants) == {'prefixes', 'singles'}
selection_profile = json.loads(git('show', SOURCE + ':tools/production-profile.json'))
required_inputs = set(constants['singles']) | set(selection_profile['files_sha256']) | {selection_profile['decision']}
required_inputs.update(selection_profile[key]['path'] for key in
    ('qualification', 'combined_regression', 'normal_command_verification', 'corrected_netlist_pair'))
release_paths = set(git('ls-tree', '-r', '--name-only', SOURCE).decode().splitlines())
expected_inputs = {name for name in release_paths if name.startswith(constants['prefixes']) or name in required_inputs}
assert required_inputs <= expected_inputs and set(index['files']) == expected_inputs
assert 'docs/specs/g4-submission-candidate.md' in index['files']
inputs = base / 'inputs'
assert not inputs.exists()
names = sorted(index['files'])
# Extract every current verification input from canonical release Git bytes.
for offset in range(0, len(names), 100):
    selected = names[offset:offset + 100]
    packed = git('archive', '--format=tar', SOURCE, '--', *selected)
    seen = set()
    with tarfile.open(fileobj=io.BytesIO(packed)) as archive:
        for entry in archive:
            if entry.isdir():
                continue
            assert entry.isfile() and entry.name in selected and entry.name not in seen
            seen.add(entry.name)
            path = (inputs / entry.name).resolve()
            assert path.is_relative_to(inputs)
            raw = archive.extractfile(entry).read()
            assert raw_sha(raw) == index['files'][entry.name], entry.name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    assert seen == set(selected)
sys.path.insert(0, str(inputs))
sys.path.insert(0, str(inputs / 'tools'))
from current_run import STAGES, retained_files, semantic_check
from current_profile import describe
from tools.production_sram import verify
production = verify(inputs)
assert production == checked['production'] == g3['production']
assert Path(sys.modules['current_profile'].__file__).resolve().is_relative_to(inputs)
assert Path(sys.modules['current_run'].__file__).resolve().is_relative_to(inputs)
assert Path(sys.modules['tools.production_sram'].__file__).resolve().is_relative_to(inputs)
profile = describe(inputs / 'src')
assert evidence['status'] == 'PASS' and evidence['profile'] == profile
assert evidence['verification_inputs'] == index['files'] and set(evidence['stages']) == set(STAGES)
assert read(pubdir / 'production-verification.json') == evidence
stages, runtime = {}, None
for action in STAGES:
    receipt = read(pipeline / 'receipts' / (action + '.json'))
    assert receipt == evidence['stages'][action]
    assert receipt['status'] == 'PASS' and receipt['action'] == action and receipt['profile'] == profile
    assert receipt['git_head'] == SOURCE and receipt['source_directory'] == '/workspace/src'
    assert receipt['verification_inputs'] == index['files']
    relative = PurePosixPath(receipt['directory']).relative_to('build/current')
    stage = (pipeline / relative).resolve()
    assert stage.is_relative_to(pipeline)
    assert receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands'])
    assert receipt['artifact_sha256'] == retained_files(stage)
    stages[action] = semantic_check(action, stage, profile)
    assert stages[action] == receipt['summary'] and receipt['artifact_sha256'] == retained_files(stage)
    if action == 'doctor':
        runtime = sha(stage / 'run.log')
    assert receipt['runtime_identity'] == runtime
checks = sorted((pipeline / 'runs').glob('*-check'))
assert len(checks) == 2 and len(list((pipeline / 'runs').iterdir())) == 9
for check in checks:
    log = (check / 'run.log').read_text()
    counts = re.findall(r'^Ran (\d+) tests? in ', log, re.M)
    assert sum(map(int, counts)) == 147 and len(re.findall(r'^OK$', log, re.M)) == len(counts)
    assert not re.search(r'^(FAILED|ERROR|FAIL:)', log, re.M)
assert evidence['stages']['check']['directory'].endswith(checks[-1].name)

pub_names = {p.name for p in pubdir.iterdir() if p.is_file()}
local_names = {p.name for p in local.iterdir() if p.is_file()}
assert pub_names.isdisjoint(local_names)
assets = {a['name']: a for a in release['assets']}
assert set(assets) == pub_names | local_names and len(assets) == len(release['assets'])
files = base / 'downloaded'
assert not files.exists()
files.mkdir()

def download(meta):
    name = meta['name']
    assert re.fullmatch(r'[A-Za-z0-9_.-]+', name) and name not in ('.', '..')
    url = meta['browser_download_url']
    assert url.startswith('https://github.com/' + REPO + '/releases/download/' + TAG + '/')
    path = files / name
    request = urllib.request.Request(url, headers={'User-Agent': 'protocol-emulator-release-audit'})
    with urllib.request.urlopen(request, timeout=60) as response, path.open('wb') as stream:
        assert response.status == 200
        while block := response.read(1024 * 1024):
            stream.write(block)
    digest = sha(path)
    assert path.stat().st_size == meta['size'] and meta['digest'] == 'sha256:' + digest
    expected = local / name if name in local_names else pubdir / name
    assert sha(expected) == digest, name
    return name, {'id': meta['id'], 'bytes': meta['size'], 'sha256': digest,
                  'anonymous_download_verified': True, 'url': url}

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    downloaded = dict(pool.map(download, assets.values()))
for name in ('SHA256SUMS', 'g4-SHA256SUMS'):
    listed = set()
    for line in (files / name).read_text().splitlines():
        digest, member = line.split('  ', 1)
        assert member not in listed and re.fullmatch('[0-9a-f]{64}', digest)
        listed.add(member)
        assert member in downloaded and downloaded[member]['sha256'] == digest
    assert listed == (pub_names if name == 'SHA256SUMS' else local_names) - {name}
publication = read(files / 'publication.json')
assert publication['source_commit'] == SOURCE and publication['ref'] == 'refs/tags/' + TAG
assert publication['verification_run'] == f'https://github.com/{REPO}/actions/runs/{run["id"]}'
assert publication['physical_qualification'] == 'NOT_EVALUATED'
assert publication['production_qualification'] == production
assert publication['checks'] == ['doctor', 'check', 'lint', 'test', 'test-verilator', 'formal', 'synth', 'evidence',
    'spi-program-sensitivity', 'spi-four-mode-screen', 'spi-held-program-proof', 'spi-phase1-capacity', 'spi-timed-gpio']
assert sha(files / 'toolchain.lock.json') == publication['toolchain_lock_sha256'] == index['files']['tools/workbench/toolchain.lock.json']
assert sha(files / 'production-profile.json') == production['profile_sha256']
assert read(files / 'g4-submission.json') == g4
for name, asset in g4['artifacts'].items():
    assert sha(files / name) == asset['sha256'] and (files / name).stat().st_size == asset['bytes']
assert (files / 'g4-public-programs.zip').read_bytes() == (frozen / '14022181491.zip').read_bytes()
assert (files / 'g4-windows-programs.zip').read_bytes() == (frozen / '14022515054.zip').read_bytes()
bundle = audit.zip_files(files / 'g4-submission-bundle.zip')
assert {name: raw_sha(raw) for name, raw in bundle.items()} == g4['bundle_members_sha256']
assert len(g4['compiled_members_sha256']) == len(windows) == 53
source_members = g4['source_members_sha256']
frozen_members = g4['frozen_evidence_members_sha256']
assert set(source_members).isdisjoint(frozen_members)
for name, expected in {**source_members, **frozen_members}.items():
    assert raw_sha(bundle[name]) == expected == raw_sha(git('show', SOURCE + ':' + name)), name
for name, expected in g4['compiled_members_sha256'].items():
    assert bundle['compiled/' + name] == windows[name] and raw_sha(windows[name]) == expected
internal = json.loads(bundle['g4-submission.json'])
assert internal == {k: v for k, v in g4.items() if k not in ('artifacts', 'bundle_members_sha256')}
# Generated files must be identified explicitly; no unexplained bundle members.
assert set(bundle) == set(source_members) | set(frozen_members) | \
    {'compiled/' + name for name in g4['compiled_members_sha256']} | \
    {'README.md', 'restore-originals.py', 'g4-submission.json'}

# Re-audit the actual public physical archives with the committed frozen audit.
# No GitHub Actions download or newer repository helper substitutes for these bytes.
physical_results, physical_archive_count, physical_members = {}, 0, 0
original_archives = g4['original_archives']
assert len(original_archives) == 14
assert len({row['asset'] for row in original_archives}) == 14
assert {row['role'] for row in original_archives} == {'candidate', 'reproduction', 'g3-public', 'g3-windows'}
for role, artifact_id in (('g3-public', 14022181491), ('g3-windows', 14022515054)):
    rows = [row for row in original_archives if row['role'] == role]
    assert len(rows) == 1
    row = rows[0]
    assert row['run_id'] == audit.RUN and row['artifact_id'] == artifact_id
    name = 'g4-' + role.removeprefix('g3-') + '-programs.zip'
    assert row['asset'] == name and row['bytes'] == (files / name).stat().st_size
    assert row['sha256'] == sha(files / name)
    assert row['storage'] == [{'path': f'evidence/E0046-program-toolchain/ci-0297655/{artifact_id}.zip',
                               'bytes': row['bytes'], 'sha256': row['sha256']}]
assert set(g4['physical_runs']) == set(PHYSICAL_RUNS)
for role, run_id in PHYSICAL_RUNS.items():
    declared = g4['physical_runs'][role]
    directory_name = f'evidence/E0047-g4-submission-candidate/ci-{run_id}'
    retained = ROOT / directory_name
    assert declared['run_id'] == run_id and declared['source_commit'] == PHYSICAL_SOURCE
    assert declared['result_path'] == directory_name + '/result.json'
    result_raw = git('show', SOURCE + ':' + declared['result_path'])
    result = json.loads(result_raw)
    assert raw_sha(result_raw) == declared['result_sha256']
    assert result['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES'
    assert result['run_id'] == run_id and result['source_commit'] == PHYSICAL_SOURCE
    assert result['production'] == production
    assert result['staged_sha256'] == production['files_sha256']
    # All executable audit dependencies and their frozen indexes come from this tag.
    for required in ('audit.py', 'sram_official_frozen_support.py', 'flow_audit.py',
                     'audit-baseline.json', 'producer.json', 'producer.tar.gz',
                     'run.json', 'jobs.json', 'artifacts.json', 'zip-files.json', 'result.json',
                     'gds-job.log.gz', 'precheck-job.log.gz', 'gl_test-job.log.gz'):
        name = directory_name + '/' + required
        assert name in frozen_members, 'missing frozen physical audit dependency: ' + name
        assert raw_sha((ROOT / name).read_bytes()) == frozen_members[name], name
    replay = base / ('physical-' + role)
    assert not replay.exists()
    replay.mkdir()
    for name in ('run.json', 'jobs.json', 'artifacts.json'):
        (replay / name).write_bytes(bundle[directory_name + '/' + name])
    for kind in ('gds', 'precheck', 'gl_test'):
        (replay / (kind + '-job.log')).write_bytes(gzip.decompress(bundle[directory_name + '/' + kind + '-job.log.gz']))
    api = read(replay / 'artifacts.json')['artifacts']
    indexed = json.loads(bundle[directory_name + '/zip-files.json'])
    rows = [row for row in original_archives if row['role'] == role]
    assert len(rows) == 6 and {row['run_id'] for row in rows} == {run_id}
    assert {a['name'] for a in api if a['id'] in {row['artifact_id'] for row in rows}} == set(result['archives']) == set(indexed)
    for row in rows:
        meta_physical = next(a for a in api if a['id'] == row['artifact_id'])
        name = meta_physical['name']
        assert row['asset'] == f'g4-{run_id}-{name}.zip'
        path = files / row['asset']
        assert row['bytes'] == meta_physical['size_in_bytes'] == path.stat().st_size
        assert 'sha256:' + row['sha256'] == meta_physical['digest']
        assert sha(path) == row['sha256'] == result['archives'][name]['sha256']
        assert row['artifact_id'] == result['archives'][name]['id']
        assert meta_physical['workflow_run']['id'] == run_id
        assert meta_physical['workflow_run']['head_sha'] == PHYSICAL_SOURCE
        # Storage pieces are checked against committed bytes, then against the
        # unmodified ZIP bytes that were actually downloaded anonymously.
        joined = hashlib.sha256()
        total = 0
        with path.open('rb') as stream:
            for piece in row['storage']:
                raw = git('show', SOURCE + ':' + piece['path'])
                assert len(raw) == piece['bytes'] and raw_sha(raw) == piece['sha256']
                assert stream.read(len(raw)) == raw
                joined.update(raw)
                total += len(raw)
            assert not stream.read(1)
        assert total == row['bytes'] and joined.hexdigest() == row['sha256']
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            assert len(members) == len({m.filename for m in members}) and archive.testzip() is None
            observed = {m.filename: raw_sha(archive.read(m)) for m in members if not m.is_dir()}
        assert observed == indexed[name]
        physical_members += len(observed)
        os.link(path, replay / (str(row['artifact_id']) + '.zip'))
        physical_archive_count += 1
    execution = subprocess.run([sys.executable, str(retained / 'audit.py'), '--directory', str(replay),
        '--output', str(replay / 'audit')], cwd=ROOT, capture_output=True, timeout=600)
    (replay / 'replay.log').write_bytes(execution.stdout + execution.stderr)
    assert execution.returncode == 0, (role, execution.stderr[-2000:])
    assert read(replay / 'audit/result.json') == result
    producing = read(retained / 'producer.json')
    assert producing['files'] == {p.relative_to(replay / 'audit/producer').as_posix(): sha(p)
                                 for p in (replay / 'audit/producer').rglob('*') if p.is_file()}
    physical_results[role] = result

reproduction = g4['reproduction']
assert reproduction['path'] == 'evidence/E0047-g4-submission-candidate/reproduction.json'
reproduction_raw = git('show', SOURCE + ':' + reproduction['path'])
assert raw_sha(reproduction_raw) == reproduction['sha256']
assert json.loads(reproduction_raw) == reproduction['record']
assert reproduction['record']['status'] == 'PASS_REPRODUCED_G4_PHYSICAL_CANDIDATE'
assert reproduction['record']['source_commit'] == PHYSICAL_SOURCE
for role, result in physical_results.items():
    pointer = reproduction['record']['runs'][role]
    assert pointer['run_id'] == result['run_id']
    assert pointer['result_path'] == g4['physical_runs'][role]['result_path']
    assert pointer['result_sha256'] == g4['physical_runs'][role]['result_sha256']
# Recompute geometry identity from the submitted GDS in the downloaded archives.
spec = importlib.util.spec_from_file_location('g4_gds_records', inputs / 'tools/compare_gds_records.py')
gds_audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gds_audit)
geometry = {}
for role, result in physical_results.items():
    replay = base / ('physical-' + role)
    submission = replay / (str(result['archives']['tt_submission']['id']) + '.zip')
    with zipfile.ZipFile(submission) as archive:
        raw = archive.read('tt_submission/tt_um_khangelani_protocol_emulator.gds')
        assert raw_sha(raw) == result['gds_sha256']
        path = replay / 'submitted.gds'
        path.write_bytes(raw)
        assert raw_sha(archive.read('tt_submission/tt_um_khangelani_protocol_emulator.v')) == result['netlist_sha256']
    _, records = gds_audit.parse_records(path)
    assert all(length == 28 and data_type == 2 for length, kind, data_type, raw in records
               if kind in gds_audit.TIMESTAMP_RECORDS), 'invalid GDS timestamp record'
    geometry[role] = path
compared_gds = gds_audit.compare(geometry['candidate'], geometry['reproduction'])
assert compared_gds['equivalent_except_timestamps'], 'released GDS geometry did not reproduce'
left, right = physical_results['candidate'], physical_results['reproduction']
for key in ('netlist_sha256', 'staged_sha256', 'macro_views', 'physical_metrics', 'area'):
    assert left[key] == right[key], 'released physical reproduction differs: ' + key
assert left['netlist_tests']['records'] == right['netlist_tests']['records']
assert left['uart_landmarks'] == right['uart_landmarks']
write(base / 'downloaded-gds-comparison.json', compared_gds)

# Preserve G2 as an earlier, separately measured qualification. Inspect its
# original submission from the downloaded bundle without calling it a G4 run.
g2_directory = 'evidence/E0045-g2-sram-qualification/ci-94a3082'
g2_qualification = selection_profile['qualification']
assert g2_qualification['path'] == g2_directory + '/result.json'
for name in ('14004891901.zip', 'result.json', 'artifacts.json'):
    assert g2_directory + '/' + name in frozen_members
g2_raw = bundle[g2_directory + '/result.json']
assert raw_sha(g2_raw) == g2_qualification['sha256']
g2_result = json.loads(g2_raw)
assert g2_result['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES'
assert all(g2_result[key] == g2_qualification[key]
           for key in ('run_id', 'source_commit', 'gds_sha256', 'netlist_sha256'))
g2_api = json.loads(bundle[g2_directory + '/artifacts.json'])['artifacts']
g2_meta = next(a for a in g2_api if a['name'] == 'tt_submission')
assert g2_meta['id'] == 14004891901 and g2_meta['workflow_run']['id'] == g2_result['run_id']
assert g2_meta['workflow_run']['head_sha'] == g2_result['source_commit']
g2_zip = bundle[g2_directory + '/14004891901.zip']
assert len(g2_zip) == g2_meta['size_in_bytes'] and 'sha256:' + raw_sha(g2_zip) == g2_meta['digest']
with zipfile.ZipFile(io.BytesIO(g2_zip)) as archive:
    raw = archive.read('tt_submission/tt_um_khangelani_protocol_emulator.gds')
    assert raw_sha(raw) == g2_result['gds_sha256']
    g2_gds = base / 'g2-original-submitted.gds'
    g2_gds.write_bytes(raw)
    assert raw_sha(archive.read('tt_submission/tt_um_khangelani_protocol_emulator.v')) == g2_result['netlist_sha256']
_, records = gds_audit.parse_records(g2_gds)
assert all(length == 28 and data_type == 2 for length, kind, data_type, raw in records
           if kind in gds_audit.TIMESTAMP_RECORDS), 'invalid original G2 timestamp record'
compared_g2 = gds_audit.compare(g2_gds, geometry['candidate'])
write(base / 'downloaded-g2-comparison.json', compared_g2)
g2_continuity = {'run_id': g2_result['run_id'], 'source_commit': g2_result['source_commit'],
    'result_sha256': raw_sha(g2_raw), 'original_submission_archive_sha256': raw_sha(g2_zip),
    'geometry_equivalent_except_timestamps': compared_g2['equivalent_except_timestamps'],
    'netlist_identical': g2_result['netlist_sha256'] == left['netlist_sha256'],
    'physical_metrics_identical': g2_result['physical_metrics'] == left['physical_metrics'],
    'area_identical': g2_result['area'] == left['area'],
    'physical_inputs_identical': g2_result['staged_sha256'] == left['staged_sha256'],
    'public_records_identical': g2_result['netlist_tests']['records'] == left['netlist_tests']['records'],
    'scope': 'Separate continuity comparison with the original G2 result; original measurements remain unchanged.'}
source_hashes = {}
for name in sorted(pub_names):
    if not name.startswith('spi-') or not name.endswith('.json'):
        continue
    value = read(files / name)
    for path, digest in value.get('input_sha256', {}).items():
        assert raw_sha(git('show', SOURCE + ':' + path)) == digest
        assert path not in source_hashes or source_hashes[path] == digest
        source_hashes[path] = digest
prior = {'spi-sensitivity.json': 'PASS', 'spi-four-mode.json': 'PASS_SCOPED_SCREEN',
         'spi-held-proof.json': 'PROVED_HELD_MODE0_MODE2_WITH_CHECKED_CONTROLS',
         'spi-phase1-capacity.json': 'PASS_DECLARED_PHASE1_CAPACITY_SCREEN'}
for name, status in prior.items():
    value = read(files / name)
    assert value['status'] == status
    if 'tasks' in value:
        assert all(t['accepted'] and not t['timed_out'] and t['status'] == t['expected'] for t in value['tasks'])
timed = read(files / 'spi-timed-gpio.json')
assert timed['status'] == 'QUALIFIED_COMPARISON' and timed['selected_candidate'] == 'P'
assert timed['candidate_qualification'] == {'P': 'PASS', 'F': 'PASS'}
assert set(timed['gates']) == {'comparison', 'instruction_p', 'instruction_f', 'program_p', 'program_f', 'refinement_p', 'refinement_f'}
for name, gate in timed['gates'].items():
    path = files / ('spi-timed-' + name + '.json')
    assert sha(path) == gate['result_sha256'] and read(path)['status'] == gate['status']
    assert gate['run']['returncode'] == 0 and not gate['run']['timed_out']
comparison = read(files / 'spi-timed-comparison.json')
reference = json.loads(git('show', SOURCE + ':evidence/E0030-timed-gpio-comparison/comparison/result.json'))
assert comparison['measurements'] == reference['measurements'] and comparison['public'] == reference['public']
assert comparison['cross_simulator_records_identical'] and comparison['cross_variant_spi_contract_traces_identical']
for variant, value in comparison['sources'].items():
    assert value['source_sha256'] == reference['sources'][variant]['source_sha256']

registry = 'kg-khangelani/protocol-emulator-asic-workbench'
prefix = 'ghcr.io/' + registry + '@'
assert publication['image'].startswith(prefix)
digest = publication['image'].removeprefix(prefix)
token_url = 'https://ghcr.io/token?' + urllib.parse.urlencode({'service': 'ghcr.io', 'scope': 'repository:' + registry + ':pull'})
with urllib.request.urlopen(token_url, timeout=30) as response:
    token = json.load(response)['token']
headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.oci.image.index.v1+json,application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'}

def registry_get(path):
    with urllib.request.urlopen(urllib.request.Request('https://ghcr.io/v2/' + registry + '/' + path, headers=headers), timeout=30) as response:
        return response.read()

raw = registry_get('manifests/' + digest)
assert 'sha256:' + raw_sha(raw) == digest
(base / 'registry-manifest.json').write_bytes(raw)
manifest, tag_digests = json.loads(raw), {}
for tag in (TAG, 'sha-' + SOURCE):
    value = 'sha256:' + raw_sha(registry_get('manifests/' + tag))
    assert value == digest
    tag_digests[tag] = value
child_digest = digest
if 'manifests' in manifest:
    matches = [m for m in manifest['manifests'] if m.get('platform', {}).get('os') == 'linux' and m.get('platform', {}).get('architecture') == 'amd64']
    assert len(matches) == 1
    child_digest = matches[0]['digest']
    raw = registry_get('manifests/' + child_digest)
    assert 'sha256:' + raw_sha(raw) == child_digest
    (base / 'registry-linux-amd64.json').write_bytes(raw)
    manifest = json.loads(raw)
raw = registry_get('blobs/' + manifest['config']['digest'])
assert 'sha256:' + raw_sha(raw) == manifest['config']['digest']
(base / 'registry-config.json').write_bytes(raw)
config = json.loads(raw)
labels = config['config']['Labels']
assert config['os'] == 'linux' and config['architecture'] == 'amd64'
assert labels['org.opencontainers.image.revision'] == labels['org.opencontainers.image.version'] == SOURCE
assert labels['org.opencontainers.image.source'] == 'https://github.com/' + REPO
inspect = read(files / 'image-inspect.json')
assert len(inspect) == 1 and inspect[0]['Id'] == manifest['config']['digest']
assert inspect[0]['Config']['Labels'] == labels
joblog = (base / 'current-job.log').read_text(encoding='utf-8-sig')
image_ids = re.findall(r'"containerimage.config.digest": "(sha256:[0-9a-f]{64})"', joblog)
assert image_ids == [inspect[0]['Id']]
assert f'Artifact ID {meta["id"]}' in joblog and meta['digest'].removeprefix('sha256:') in joblog

def head_layer(layer):
    request = urllib.request.Request('https://ghcr.io/v2/' + registry + '/blobs/' + layer['digest'], headers=headers, method='HEAD')
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200 and int(response.headers['Content-Length']) == layer['size']
        return {'digest': layer['digest'], 'bytes': layer['size'], 'anonymous_head_status': response.status}

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    layers = list(pool.map(head_layer, manifest['layers']))
result = {'schema': 'protocol-emulator-g4-release-verification-v1', 'status': 'PASS_G4_RELEASE_AND_PACKAGE',
          'observed_utc': datetime.now(timezone.utc).isoformat(), 'tag': TAG, 'release_id': release['id'],
          'url': release['html_url'], 'source_commit': SOURCE, 'physical_source_commit': PHYSICAL_SOURCE,
          'publish_run': run['id'], 'publication_job_id': job['id'], 'publication_artifact_id': meta['id'],
          'publication_original_zip_sha256': sha(original), 'publication_original_zip_files': len(zip_members),
          'assets': downloaded, 'g3_original_ci_archives_verified': 2,
          'physical_original_ci_archives_verified': physical_archive_count,
          'physical_original_archive_members_verified': physical_members,
          'physical_runs_reaudited_from_public_downloads': {role: {'run_id': value['run_id'],
              'status': value['status'], 'result_sha256': g4['physical_runs'][role]['result_sha256']}
              for role, value in physical_results.items()},
          'reproduction_record_sha256': reproduction['sha256'],
          'downloaded_gds_comparison_sha256': sha(base / 'downloaded-gds-comparison.json'),
          'downloaded_geometry_equivalent_except_timestamps': True,
          'g2_continuity_recomputed': g2_continuity,
          'downloaded_g2_comparison_sha256': sha(base / 'downloaded-g2-comparison.json'),
          'source_bundle_files_identical_to_release_git_blobs': len(source_members),
          'frozen_evidence_bundle_files_identical_to_release_git_blobs': len(frozen_members),
          'compiled_artifacts_identical_to_original_windows_linux_and_clean_clone': len(windows),
          'bundle_members_verified': len(bundle),
          'current_verification_input_files_bound_to_release_git': len(index['files']),
          'verification_input_files_unchanged_from_clean_G3_CI': len(historical_inputs),
          'qualification_source_commit': audit.SOURCE, 'qualification_run_id': audit.RUN,
          'publication': publication, 'production_stages': stages, 'metadata_check_executions': 2, 'metadata_tests_each': 147,
          'verified_spi_input_hashes': source_hashes, 'prior_spi_gates': prior, 'timed_gate_count': len(timed['gates']),
          'timed_generic_selection': 'P', 'timed_measurements_and_record_hashes_match_e0030': True,
          'image': publication['image'], 'verified_tag_digests': tag_digests, 'manifest_digest': digest,
          'linux_amd64_manifest_digest': child_digest, 'config_digest': manifest['config']['digest'],
          'anonymous_layer_heads': layers, 'tag_workflows': tag_jobs,
          'registry_verification_scope': 'Manifest/config bodies downloaded and hashed; all layer read permissions and sizes checked by anonymous HEAD, without downloading layer bodies.',
          'scope': 'Stable v0.1.0 assets, software distribution, two fresh production physical qualifications reproduced from actual public downloads, exact version/source/image identity, complete normal-command release verification and preserved historical gates. This audits submission material; it does not submit an entry or establish silicon, analog compliance, measured Fmax, unrestricted interoperability or owner fluency.'}
write(base / 'release-verification.json', result)
print(json.dumps({'status': result['status'], 'assets': len(downloaded), 'bundle_members': len(bundle),
                  'publication_files': len(zip_members), 'image': publication['image'], 'layer_heads': len(layers),
                  'tag_workflows': len(tag_jobs)}, indent=2))
