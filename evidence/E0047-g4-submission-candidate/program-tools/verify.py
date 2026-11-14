# SPDX-License-Identifier: Apache-2.0
"""Audit fresh G4 program CI from retained original archives and frozen producing source."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = 'ae2ac7bf800bd02d83fe62677a56bc4131e98b06'
RUN = 43544749692
COUNTS = {'loader': 7, 'uart_tx': 3, 'uart_rx': 2, 'spi': 25, 'i2c': 18}
GROUPS = {'assembled_loader_controls', 'assembled_uart_examples', 'assembled_spi_examples', 'assembled_i2c_examples'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


HERE = Path(__file__).resolve().parent
_producer = None


def producer():
    global _producer
    if _producer is None:
        index = read(HERE / 'producer.json')
        raw = (HERE / 'producer.tar.gz').read_bytes()
        assert index['source_commit'] == SOURCE and sha(raw) == index['sha256'], 'frozen producer identity differs'
        files = {}
        with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
            for entry in archive:
                name = PurePosixPath(entry.name)
                assert entry.isfile() and entry.name not in files
                assert not name.is_absolute() and '..' not in name.parts and '\\' not in entry.name
                files[entry.name] = archive.extractfile(entry).read()
        assert {n: sha(raw) for n, raw in files.items()} == index['files'], 'frozen source bytes differ'
        assert all(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == index['git_blob_sha1'][n]
                   for n, raw in files.items()), 'canonical Git blob identity differs'
        _producer = (index, files)
    return _producer


def git(*args):
    # Compatibility adapter for the original audit's source reads; no Git or network execution.
    assert len(args) == 2 and args[0] == 'show' and args[1].startswith(SOURCE + ':')
    return producer()[1][args[1].split(':', 1)[1]]


def committed_inputs(inputs):
    index, files = producer()
    assert inputs == index['verification_inputs_sha256'], 'producing input set differs'
    assert all(sha(files[n]) == digest for n, digest in inputs.items()), 'producing source digest differs'


def zip_files(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        assert len(entries) == len({e.filename for e in entries}) and archive.testzip() is None
        files = {}
        for entry in entries:
            name = PurePosixPath(entry.filename)
            assert not name.is_absolute() and '..' not in name.parts and '\\' not in entry.filename
            if not entry.is_dir():
                files[entry.filename] = archive.read(entry)
        return files


def check_public(files):
    result = json.loads(files['result.json'])
    assert result['status'] == 'PASS_ASSEMBLER_AND_BOTH_PUBLIC_SIMULATORS'
    assert result['source_commit'] == SOURCE
    assert len(result['inputs_sha256']) == 352, 'producing input count differs'
    committed_inputs(result['inputs_sha256'])
    assert len(result['stages']) == 4 and all(s['returncode'] == 0 for s in result['stages'])
    assert result['stages'][0]['command'][1:] == ['tools/doctor.py']
    assert result['stages'][0]['log_sha256'] == sha(files['doctor.log'])
    assert result['stages'][1]['command'][1:] == ['-m', 'unittest', 'discover', '-s', 'test', '-p', 'test_program_tools.py']
    assert result['stages'][1]['log_sha256'] == sha(files['unit-tests.log'])
    doctor = files['doctor.log'].decode('utf-8')
    assert 'locked workbench: exact versions required' in doctor
    assert not re.search(r'^FAIL:', doctor, re.MULTILINE)
    unit = files['unit-tests.log'].decode('utf-8')
    assert re.search(r'Ran 20 tests in .*\n\s*\nOK', unit)
    production = json.loads(git('show', SOURCE + ':evidence/E0045-g2-sram-qualification/ci-default-75c1e7d/verification.json'))['production']
    assert result['production'] == production
    records = {}
    for simulator in ('icarus', 'verilator'):
        prefix = simulator + '/'
        root = ET.fromstring(files[prefix + 'results.xml'])
        cases = root.findall('.//testcase')
        assert len(cases) == 4 and {c.get('name') for c in cases} == GROUPS and all(not list(c) for c in cases), 'required public group failed or skipped'
        records[simulator] = sorted((json.loads(line) for line in files[prefix + 'records/records.jsonl'].splitlines()), key=lambda r: r['name'])
        rows = records[simulator]
        assert len(rows) == len({r['name'] for r in rows}) == 55
        assert {group: sum(r['group'] == group for r in rows) for group in COUNTS} == COUNTS
        assert sum(not r['expected_acceptance'] for r in rows) == 15
        for row in rows:
            raw = gzip.decompress(files[prefix + 'records/' + row['name'] + '.json.gz'])
            assert sha(raw) == row['trace_sha256'] and len(json.loads(raw)) == row['observations'] > 0
            if row['group'] != 'loader':
                assert row['accepted'] == row['expected_acceptance']
                if row['group'] in ('spi', 'i2c'):
                    assert bool(row['errors']) != row['expected_acceptance']
            elif not row['expected_acceptance']:
                assert row['rejected']
        assert result[simulator]['records'] == rows
        assert result[simulator]['junit_sha256'] == sha(files[prefix + 'results.xml'])
        stage = next(s for s in result['stages'] if 'SIM=' + simulator in s['command'])
        assert 'SRC_DIR=/workspace/src' in stage['command']
        assert stage['log_sha256'] == sha(files[prefix + 'public-pins.log'])
        log = files[prefix + 'public-pins.log'].decode('utf-8')
        assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in log
        assert '-DGL_TEST' in log and '/workspace/src/project.v' in log
    assert records['icarus'] == records['verilator']
    catalog = json.loads(git('show', SOURCE + ':programs/od128-sram-v1/examples.json'))
    manifest = json.loads(files['examples/manifest.json'])
    assert manifest == result['build'] and len(manifest['examples']) == 13
    for example in catalog['examples']:
        name = example['name']
        prefix = 'examples/' + name + '/'
        image = json.loads(files[prefix + 'program.json'])
        binary = files[prefix + 'program.bin']
        assert image['words'] == example['expected_words']
        assert binary == b''.join(int(w, 16).to_bytes(4, 'little') for w in image['words']), 'compiled binary differs from catalog'
        assert image['binary_sha256'] == example['binary_sha256'] == sha(binary)
        assert image['source_sha256'] == sha(git('show', SOURCE + ':programs/od128-sram-v1/' + example['file']))
        for path, digest in manifest['examples'][name]['artifact_sha256'].items():
            assert sha(files[prefix + path]) == digest
    return result


def audit(base):
    run, jobs, artifacts = (read(base / name) for name in ('run.json', 'jobs.json', 'artifacts.json'))
    assert run['id'] == RUN and run['head_sha'] == SOURCE and run['path'] == '.github/workflows/program-tools.yaml'
    assert run['event'] == 'push' and run['status'] == 'completed' and run['conclusion'] == 'success', 'program-tools workflow is incomplete'
    assert len(jobs['jobs']) == 2 and len({job['name'] for job in jobs['jobs']}) == 2
    jobs = {job['name']: job for job in jobs['jobs']}
    assert set(jobs) == {'public-programs', 'windows-assembly'}
    for job in jobs.values():
        assert job['run_id'] == RUN and job['run_attempt'] == run['run_attempt'] and job['head_sha'] == SOURCE
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(step['conclusion'] == 'success' for step in job['steps'])
    assert artifacts['total_count'] == len(artifacts['artifacts'])
    assert len({a['id'] for a in artifacts['artifacts']}) == artifacts['total_count']
    artifact_ids = {}
    for kind in ('public', 'windows'):
        selected = [a for a in artifacts['artifacts'] if a['name'] == f'program-tools-{kind}-' + SOURCE]
        assert len(selected) == 1, 'missing or duplicate program archive'
        artifact_ids[kind] = selected[0]['id']
    excluded_artifacts = [a for a in artifacts['artifacts'] if a['id'] not in artifact_ids.values()]
    assert all(a['name'].startswith('KG-khangelani~protocol-emulator-asic~') and
               a['name'].endswith('.dockerbuild') for a in excluded_artifacts), 'unexpected extra CI artifact'
    unpacked, identities = {}, {}
    for kind, artifact_id in artifact_ids.items():
        meta = next(a for a in artifacts['artifacts'] if a['id'] == artifact_id)
        assert meta['name'] == f'program-tools-{kind}-' + SOURCE and not meta['expired']
        assert meta['workflow_run']['id'] == RUN and meta['workflow_run']['head_sha'] == SOURCE
        path = base / (str(artifact_id) + '.zip')
        assert len(path.read_bytes()) == meta['size_in_bytes']
        assert 'sha256:' + sha(path.read_bytes()) == meta['digest'], 'original archive digest differs'
        unpacked[kind] = zip_files(path)
        log = gzip.decompress((base / (kind + '-job.log.gz')).read_bytes()).decode('utf-8-sig')
        assert f'Artifact ID {artifact_id}' in log and meta['digest'].removeprefix('sha256:') in log
        identities[kind] = {'id': artifact_id, 'sha256': meta['digest'].removeprefix('sha256:'),
                            'bytes': meta['size_in_bytes'], 'files': len(unpacked[kind])}
    public = check_public(unpacked['public'])
    window_files = unpacked['windows']
    public_examples = {path.removeprefix('examples/'): raw for path, raw in unpacked['public'].items() if path.startswith('examples/')}
    assert window_files == public_examples and len(window_files) == 53
    inspected = json.loads(unpacked['public']['workbench-image.json'])
    assert len(inspected) == 1 and inspected[0]['Os'] == 'linux' and inspected[0]['Architecture'] == 'amd64'
    public_log = gzip.decompress((base / 'public-job.log.gz').read_bytes()).decode('utf-8-sig')
    configs = re.findall(r'"containerimage.config.digest": "(sha256:[0-9a-f]{64})"', public_log)
    assert configs == [inspected[0]['Id']]
    baseline_path = 'evidence/E0046-program-toolchain/ci-0297655/'
    baseline_verification = json.loads(git('show', SOURCE + ':' + baseline_path + 'verification.json'))
    assert baseline_verification['status'] == 'PASS_G3_CLEAN_CHECKOUT_AND_CI' and baseline_verification['run_id'] == 43393826878
    baseline_archive = git('show', SOURCE + ':' + baseline_path + '14022181491.zip')
    old_identity = baseline_verification['artifacts']['public']
    assert old_identity['sha256'] == sha(baseline_archive) and old_identity['bytes'] == len(baseline_archive)
    with zipfile.ZipFile(io.BytesIO(baseline_archive)) as archive:
        assert archive.testzip() is None
        historical = {e.filename: archive.read(e) for e in archive.infolist() if not e.is_dir()}
    assert baseline_verification['archive_members']['public'] == {n: sha(raw) for n, raw in historical.items()}
    old_result = json.loads(historical['result.json'])
    assert old_result['source_commit'] == '0297655e22ded931baae483b6deff81b7c9ccffd'
    assert old_result['status'] == 'PASS_ASSEMBLER_AND_BOTH_PUBLIC_SIMULATORS'
    assert old_result['icarus']['records'] == old_result['verilator']['records']
    old_inputs, new_inputs = old_result['inputs_sha256'], public['inputs_sha256']
    assert len(old_inputs) == 351 and all(new_inputs.get(n) == h for n, h in old_inputs.items()), 'G3 producing input changed'
    additions = {n: h for n, h in new_inputs.items() if n not in old_inputs}
    assert set(additions) == {'docs/specs/g4-submission-candidate.md'}, 'unexpected source-input addition'
    assert old_result['icarus']['records'] == public['icarus']['records'], 'G3 public observations changed'
    assert all(historical['examples/' + path] == raw for path, raw in window_files.items()), 'G3 compiled artifacts changed'
    windows_log = gzip.decompress((base / 'windows-job.log.gz').read_bytes()).decode('utf-8-sig')
    assert re.search(r'Ran 20 tests in', windows_log) and re.search(r'(?m)^.*\bOK\s*$', windows_log)
    # The exact workflow binds clean action checkouts to the observed job/source identities.
    workflow = git('show', SOURCE + ':.github/workflows/program-tools.yaml').decode()
    assert workflow.count('uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803') == 2
    assert 'build/g3-ci/workbench-image.json' in workflow and 'test_program_tools.py' in workflow
    return {'schema': 'protocol-emulator-g4-program-ci-audit-v1', 'status': 'PASS_G4_FRESH_PROGRAM_TOOLCHAIN_CI',
            'source_commit': SOURCE, 'run_id': RUN,
            'jobs': {name: {'id': job['id'], 'conclusion': job['conclusion']} for name, job in jobs.items()},
            'artifacts': identities, 'committed_verification_inputs': len(public['inputs_sha256']),
            'excluded_artifacts': [{'id': a['id'], 'name': a['name'], 'bytes': a['size_in_bytes'],
                                    'sha256': a['digest'].removeprefix('sha256:'),
                                    'reason': 'Buildx auxiliary metadata; tested image identity is bound by completed job log and image inspection.'}
                                   for a in excluded_artifacts],
            'examples': 13, 'assembler_tests': 20, 'public_cases_each': 55, 'expected_rejections_each': 15,
            'both_simulators_and_g3_records_identical': True,
            'windows_linux_and_g3_artifact_files_identical': len(window_files),
            'fresh_local_clone_simulation': 'NOT_RUN_HARDWARE_AND_SOFTWARE_UNCHANGED',
            'g3_continuity': {'source_commit': old_result['source_commit'], 'run_id': baseline_verification['run_id'],
                              'unchanged_verification_inputs': len(old_inputs), 'added_inputs': additions,
                              'original_public_archive_sha256': sha(baseline_archive)},
            'frozen_producer': {'sha256': producer()[0]['sha256'], 'files': len(producer()[1])},
            'actual_ci_image_config_digest': inspected[0]['Id'],
            'production': public['production'],
            'archive_members': {kind: {path: sha(raw) for path, raw in sorted(files.items())}
                                for kind, files in unpacked.items()},
            'scope': 'Two original fresh CI archives from separate clean Windows/Linux action checkouts; frozen producing source and unchanged G3 input/trace/program comparison. No fresh local clone simulation, physical, analog, silicon or owner-fluency claim.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to((ROOT / 'build').resolve()) and not output.exists()
    records = args.records.resolve()
    if records == HERE:
        for line in (HERE / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            expected, name = line.split('  ', 1)
            assert '/' not in name and '\\' not in name
            assert sha((HERE / name).read_bytes()) == expected, 'retained file changed: ' + name
    report = audit(records)
    if records == HERE:
        assert report == read(HERE / 'verification.json'), 'retained audit report differs'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    print(report['status'], report['committed_verification_inputs'], 'committed inputs')
