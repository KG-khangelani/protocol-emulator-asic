# SPDX-License-Identifier: Apache-2.0
"""Audit original publication CI, anonymous release downloads and exact registry identity."""
import argparse
import concurrent.futures
from datetime import datetime, timezone
import gzip
import importlib.util
import io
import hashlib
import json
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
TAG = 'v0.1.0-alpha.7'
parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
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
assert job['status'] == 'completed' and job['conclusion'] == 'success'
assert all(step['conclusion'] == 'success' for step in job['steps'])
release = read(base / 'release.json')
assert release['tag_name'] == TAG and release['prerelease'] and not release['draft']
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
local = ROOT / 'build/g3-release-assets' / SOURCE
g3 = read(local / 'g3-toolchain.json')
assert g3['release_source_commit'] == SOURCE and g3['tag'] == TAG
frozen = ROOT / 'evidence/E0046-program-toolchain/ci-0297655'
spec = importlib.util.spec_from_file_location('g3_frozen_audit', frozen / 'verify.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
checked = audit.audit(frozen)
assert checked == read(frozen / 'verification.json')
assert sha(frozen / 'verification.json') == g3['qualification_record_sha256']
public = audit.zip_files(frozen / '14022181491.zip')
windows = audit.zip_files(frozen / '14022515054.zip')
assert g3['qualification_source_commit'] == audit.SOURCE and g3['qualification_run_id'] == audit.RUN
index = {'files': json.loads(public['result.json'])['inputs_sha256']}
assert len(index['files']) == g3['verification_inputs_unchanged'] == 351
inputs = base / 'inputs'
assert not inputs.exists()
names = sorted(index['files'])
# Extract the release's canonical Git bytes, comparing each with qualified G3 inputs.
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
profile = describe(inputs / 'src')
pipeline = ci / 'build/current'
evidence = read(pipeline / 'evidence.json')
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
for name in ('SHA256SUMS', 'g3-SHA256SUMS'):
    for line in (files / name).read_text().splitlines():
        digest, member = line.split('  ', 1)
        assert member in downloaded and downloaded[member]['sha256'] == digest
publication = read(files / 'publication.json')
assert publication['source_commit'] == SOURCE and publication['ref'] == 'refs/tags/' + TAG
assert publication['verification_run'] == f'https://github.com/{REPO}/actions/runs/{run["id"]}'
assert publication['physical_qualification'] == 'NOT_EVALUATED'
assert publication['production_qualification'] == production
assert publication['checks'] == ['doctor', 'check', 'lint', 'test', 'test-verilator', 'formal', 'synth', 'evidence',
    'spi-program-sensitivity', 'spi-four-mode-screen', 'spi-held-program-proof', 'spi-phase1-capacity', 'spi-timed-gpio']
assert sha(files / 'toolchain.lock.json') == publication['toolchain_lock_sha256'] == index['files']['tools/workbench/toolchain.lock.json']
assert sha(files / 'production-profile.json') == production['profile_sha256']
assert read(files / 'g3-toolchain.json') == g3
for name, asset in g3['artifacts'].items():
    assert sha(files / name) == asset['sha256'] and (files / name).stat().st_size == asset['bytes']
assert (files / 'g3-public-programs.zip').read_bytes() == (frozen / '14022181491.zip').read_bytes()
assert (files / 'g3-windows-programs.zip').read_bytes() == (frozen / '14022515054.zip').read_bytes()
bundle = audit.zip_files(files / 'g3-program-toolchain.zip')
assert {name: raw_sha(raw) for name, raw in bundle.items()} == g3['bundle_members_sha256']
assert len(bundle) == 73 and len(g3['source_members_sha256']) == 18
assert len(g3['compiled_members_sha256']) == len(windows) == 53
for name, digest in g3['source_members_sha256'].items():
    assert raw_sha(bundle[name]) == digest == raw_sha(git('show', SOURCE + ':' + name))
for name, digest in g3['compiled_members_sha256'].items():
    assert bundle['compiled/' + name] == windows[name] and raw_sha(windows[name]) == digest
internal = json.loads(bundle['g3-toolchain.json'])
assert internal == {k: v for k, v in g3.items() if k not in ('artifacts', 'bundle_members_sha256')}
physical = read(inputs / 'tools/production-profile.json')['qualification']
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
    assert items and all(j['run_id'] == tagged['id'] and j['run_attempt'] == tagged['run_attempt'] for j in items)
    assert all(j['status'] == 'completed' and j['conclusion'] == 'success' for j in items)
    assert all(s['conclusion'] in ('success', 'skipped') for j in items for s in j['steps'])
    tag_jobs[tagged['name']] = {'run_id': tagged['id'], 'jobs': {j['name']: j['id'] for j in items},
                               'conclusion': 'success'}
assert tag_jobs['publish']['run_id'] == run['id']
result = {'schema': 'protocol-emulator-g3-release-verification-v1', 'status': 'PASS_G3_RELEASE_AND_PACKAGE',
          'observed_utc': datetime.now(timezone.utc).isoformat(), 'tag': TAG, 'release_id': release['id'],
          'url': release['html_url'], 'source_commit': SOURCE, 'physical_source_commit': physical['source_commit'],
          'publish_run': run['id'], 'publication_job_id': job['id'], 'publication_artifact_id': meta['id'],
          'publication_original_zip_sha256': sha(original), 'publication_original_zip_files': len(zip_members),
          'assets': downloaded, 'g3_original_ci_archives_verified': 2,
          'source_bundle_files_identical_to_release_git_blobs': 18,
          'compiled_artifacts_identical_to_original_windows_linux_and_clean_clone': 53,
          'bundle_members_verified': len(bundle),
          'verification_input_files_unchanged_from_clean_G3_CI': len(index['files']),
          'qualification_source_commit': audit.SOURCE, 'qualification_run_id': audit.RUN,
          'publication': publication, 'production_stages': stages, 'metadata_check_executions': 2, 'metadata_tests_each': 147,
          'verified_spi_input_hashes': source_hashes, 'prior_spi_gates': prior, 'timed_gate_count': len(timed['gates']),
          'timed_generic_selection': 'P', 'timed_measurements_and_record_hashes_match_e0030': True,
          'image': publication['image'], 'verified_tag_digests': tag_digests, 'manifest_digest': digest,
          'linux_amd64_manifest_digest': child_digest, 'config_digest': manifest['config']['digest'],
          'anonymous_layer_heads': layers, 'tag_workflows': tag_jobs,
          'registry_verification_scope': 'Manifest/config bodies downloaded and hashed; all layer read permissions and sizes checked by anonymous HEAD, without downloading layer bodies.',
          'scope': 'Alpha.7 assets, standalone toolchain, exact version/source/image identity, complete normal-command release verification and preserved historical gates. Physical qualification remains the original G2 E0045 run with identical production inputs. No silicon, analog compliance, measured Fmax, unrestricted interoperability, final-submission or owner-fluency claim.'}
write(base / 'release-verification.json', result)
print(json.dumps({'status': result['status'], 'assets': len(downloaded), 'bundle_members': len(bundle),
                  'publication_files': len(zip_members), 'image': publication['image'], 'layer_heads': len(layers),
                  'tag_workflows': len(tag_jobs)}, indent=2))
