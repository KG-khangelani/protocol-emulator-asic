# SPDX-License-Identifier: Apache-2.0
"""Audit original G3 CI archives and the separate clean committed checkout."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = '0297655e22ded931baae483b6deff81b7c9ccffd'
RUN = 43393826878
COUNTS = {'loader': 7, 'uart_tx': 3, 'uart_rx': 2, 'spi': 25, 'i2c': 18}
GROUPS = {'assembled_loader_controls', 'assembled_uart_examples', 'assembled_spi_examples', 'assembled_i2c_examples'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def committed_inputs(inputs):
    names = sorted(inputs)
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
                assert sha(archive.extractfile(entry).read()) == inputs[entry.name], entry.name
        assert seen == set(selected)


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
    assert len(result['inputs_sha256']) == 351
    committed_inputs(result['inputs_sha256'])
    assert len(result['stages']) == 4 and all(s['returncode'] == 0 for s in result['stages'])
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
        assert len(cases) == 4 and {c.get('name') for c in cases} == GROUPS and all(not list(c) for c in cases)
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
        assert binary == b''.join(int(w, 16).to_bytes(4, 'little') for w in image['words'])
        assert image['binary_sha256'] == example['binary_sha256'] == sha(binary)
        assert image['source_sha256'] == sha(git('show', SOURCE + ':programs/od128-sram-v1/' + example['file']))
        for path, digest in manifest['examples'][name]['artifact_sha256'].items():
            assert sha(files[prefix + path]) == digest
    return result


def audit(base):
    run, jobs, artifacts = (read(base / name) for name in ('run.json', 'jobs.json', 'artifacts.json'))
    assert run['id'] == RUN and run['head_sha'] == SOURCE and run['path'] == '.github/workflows/program-tools.yaml'
    assert run['event'] == 'push' and run['status'] == 'completed' and run['conclusion'] == 'success'
    jobs = {job['name']: job for job in jobs['jobs']}
    assert set(jobs) == {'public-programs', 'windows-assembly'}
    for job in jobs.values():
        assert job['run_id'] == RUN and job['run_attempt'] == run['run_attempt']
        assert job['status'] == 'completed' and job['conclusion'] == 'success'
        assert all(step['conclusion'] == 'success' for step in job['steps'])
    artifact_ids = {'public': 14022181491, 'windows': 14022515054}
    unpacked, identities = {}, {}
    for kind, artifact_id in artifact_ids.items():
        meta = next(a for a in artifacts['artifacts'] if a['id'] == artifact_id)
        assert meta['name'] == f'program-tools-{kind}-' + SOURCE and not meta['expired']
        assert meta['workflow_run']['id'] == RUN and meta['workflow_run']['head_sha'] == SOURCE
        path = base / (str(artifact_id) + '.zip')
        assert len(path.read_bytes()) == meta['size_in_bytes']
        assert 'sha256:' + sha(path.read_bytes()) == meta['digest']
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
    clone = read(base / 'clean-checkout.json')
    assert clone['source_commit'] == SOURCE and clone['clean_before_and_after'] and not clone['shared_git_objects']
    assert clone['original_zip_sha256'] == sha((base / 'clean-checkout.zip').read_bytes())
    clean = zip_files(base / 'clean-checkout.zip')
    assert clone['members'] == {path: sha(raw) for path, raw in clean.items()}
    clean_result = check_public(clean)
    assert clean_result['inputs_sha256'] == public['inputs_sha256']
    assert clean_result['icarus']['records'] == public['icarus']['records']
    assert all(clean['examples/' + path] == raw for path, raw in window_files.items())
    return {'schema': 'protocol-emulator-g3-ci-audit-v1', 'status': 'PASS_G3_CLEAN_CHECKOUT_AND_CI',
            'source_commit': SOURCE, 'run_id': RUN,
            'jobs': {name: {'id': job['id'], 'conclusion': job['conclusion']} for name, job in jobs.items()},
            'artifacts': identities, 'committed_verification_inputs': len(public['inputs_sha256']),
            'examples': 13, 'assembler_tests': 20, 'public_cases_each': 55, 'expected_rejections_each': 15,
            'both_simulators_and_clean_checkout_records_identical': True,
            'windows_linux_and_clean_checkout_artifact_files_identical': len(window_files),
            'actual_ci_image_config_digest': inspected[0]['Id'],
            'production': public['production'],
            'archive_members': {kind: {path: sha(raw) for path, raw in sorted(files.items())}
                                for kind, files in {**unpacked, 'clean-checkout': clean}.items()},
            'scope': 'Original CI archives and independent clean local clone of the committed software; unchanged G2 hardware. Program and trace identity, not a new physical or owner-learning qualification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to((ROOT / 'build').resolve()) and not output.exists()
    report = audit(args.records.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    print(report['status'], report['committed_verification_inputs'], 'committed inputs')
