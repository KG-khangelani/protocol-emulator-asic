# SPDX-License-Identifier: Apache-2.0
"""Attempt to fool the G5 retained audit with rehashed, semantically bad evidence."""
import argparse
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('g5_audit_controls', Path(__file__).with_name('verify.py'))
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as output:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            output.writestr(info, raw)
    return stream.getvalue()


def mutate(files, kind):
    result = json.loads(files['primary/result.json'])
    if kind in ('runtime-edge', 'loader-address'):
        name = 'control-phase-middle'
        path = 'primary/icarus/records/' + name + '.json.gz'
        trace = json.loads(gzip.decompress(files[path]))
        if kind == 'runtime-edge':
            assert trace['runtime'][30]['out'] == 7
            trace['runtime'][30]['out'] = 6
        else:
            row = next(row for row in trace['loader'] if row['action'] == 'write_byte')
            assert row['ui_in'] == 0xC0
            row['ui_in'] = 0xC1
        raw = (json.dumps(trace, sort_keys=True, separators=(',', ':')) + '\n').encode()
        files[path] = gzip.compress(raw, mtime=0)
        records_path = 'primary/icarus/records/records.jsonl'
        records = [json.loads(line) for line in files[records_path].splitlines()]
        for rows in (records, result['icarus']['records']):
            next(row for row in rows if row['name'] == name)['trace_sha256'] = sha(raw)
        files[records_path] = b''.join((json.dumps(row, sort_keys=True) + '\n').encode() for row in records)
    elif kind == 'runtime-image':
        for path in ('workbench-image.json', 'workbench-image-after.json'):
            image = json.loads(files[path])
            image[0]['Id'] = 'sha256:' + '0' * 64
            files[path] = encoded(image)
        runtime = json.loads(files['runtime.json'])
        runtime['image_id'] = 'sha256:' + '0' * 64
        files['runtime.json'] = encoded(runtime)
    elif kind == 'missing-junit-group':
        path = 'primary/verilator/results.xml'
        root = ET.fromstring(files[path])
        parent = next(node for node in root.iter() if any(child.tag == 'testcase' for child in node))
        parent.remove(next(child for child in parent if child.tag == 'testcase'))
        files[path] = ET.tostring(root)
        result['verilator']['junit_sha256'] = sha(files[path])
    elif kind == 'source-oracle':
        path = 'primary/source-inputs.zip'
        sources = AUDIT.zip_members(files[path])
        name = 'experiments/waveform_replay/oracle.py'
        sources[name] += b'\n# Evidence mutation, absent from claimed source commit.\n'
        files[path] = archive(sources)
        result['inputs_sha256'][name] = sha(sources[name])
        result['source']['inputs_sha256'][name] = sha(sources[name])
        result['source']['source_zip_sha256'] = sha(files[path])
        files['primary/source-inputs.json'] = encoded(result['source'])
    else:
        raise ValueError(kind)
    files['primary/result.json'] = encoded(result)
    comparison = json.loads(files['comparison/result.json'])
    comparison['first_result_sha256'] = sha(files['primary/result.json'])
    files['comparison/result.json'] = encoded(comparison)


def run(directory):
    metadata = {name: (directory / name).read_bytes() for name in ('run.json', 'jobs.json', 'artifacts.json', 'job.log.gz')}
    artifact = json.loads(metadata['artifacts.json'])['artifacts'][0]
    original = (directory / (str(artifact['id']) + '.zip')).read_bytes()
    files = AUDIT.zip_members(original)
    expected = {
        'runtime-edge': 'retained runtime fails independent reassessment',
        'loader-address': 'public reset/bank/address/write/read/commit sequence differs',
        'runtime-image': 'actual pulled image manifest/config/platform identity differs',
        'missing-junit-group': 'JUnit group selection differs',
        'source-oracle': 'producing bytes differ from committed Git blobs',
    }
    records = []
    for name, error_text in expected.items():
        altered = dict(files)
        mutate(altered, name)
        raw = archive(altered)
        changed_metadata = json.loads(metadata['artifacts.json'])
        changed_metadata['artifacts'][0].update(digest='sha256:' + sha(raw), size_in_bytes=len(raw))
        log = gzip.decompress(metadata['job.log.gz']).replace(sha(original).encode(), sha(raw).encode())
        with tempfile.TemporaryDirectory(prefix='g5-control-', dir=ROOT / 'build') as folder:
            folder = Path(folder).resolve()
            assert folder.is_relative_to((ROOT / 'build').resolve())
            for filename, data in metadata.items():
                (folder / filename).write_bytes(data)
            (folder / 'artifacts.json').write_bytes(encoded(changed_metadata))
            (folder / 'job.log.gz').write_bytes(gzip.compress(log, mtime=0))
            (folder / (str(artifact['id']) + '.zip')).write_bytes(raw)
            try:
                AUDIT.audit(folder)
            except ValueError as error:
                assert error_text in str(error), (name, str(error))
                records.append({'control': name, 'rejected': True, 'error': str(error),
                                'mutated_archive_sha256': sha(raw),
                                'changed_members': [path for path in sorted(altered) if altered[path] != files[path]]})
            else:
                raise AssertionError('audit accepted rehashed bad evidence: ' + name)
    return {'schema': 'protocol-emulator-g5-evidence-controls-v1', 'status': 'PASS_FIVE_REHASHED_CONTROLS',
            'original_artifact_sha256': sha(original), 'controls': records,
            'scope': 'Synthetic copies deliberately rehash transport metadata, logs and dependent receipts to reach semantic checks; originals are unchanged.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to((ROOT / 'build').resolve()) and not output.exists()
    result = run(args.directory.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(encoded(result))
    print(result['status'])
