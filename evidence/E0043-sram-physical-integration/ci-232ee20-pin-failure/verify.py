# SPDX-License-Identifier: Apache-2.0
"""Replay the original physical audit and preserve the independent pin rejection."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
out.mkdir(parents=True)
for name in ('14000880025.zip', '14000422018.zip', '13999644128.zip', '13999164903.zip',
             'run.json', 'jobs.json', 'artifacts.json'):
    (out / name).write_bytes((HERE / name).read_bytes())
for name in ('gds-job', 'precheck-job'):
    (out / (name + '.log')).write_bytes(gzip.decompress((HERE / (name + '.log.gz')).read_bytes()))
subprocess.run([sys.executable, str(HERE / 'audit.py'), '--directory', str(out),
                '--output', str(out / 'physical'), '--physical-only'], check=True, cwd=ROOT)
assert read(out / 'physical/result.json') == read(HERE / 'physical-review.json')
producer = read(HERE / 'producer.json')
assert producer['files'] == {p.relative_to(out / 'physical/producer').as_posix(): sha(p.read_bytes())
                            for p in (out / 'physical/producer').rglob('*') if p.is_file()}
artifacts = read(HERE / 'artifacts.json')['artifacts']
indexed = read(HERE / 'zip-files.json')
for a in artifacts:
    if a['name'] not in indexed:
        continue
    path = out / (str(a['id']) + '.zip')
    assert path.stat().st_size == a['size_in_bytes'] and 'sha256:' + sha(path.read_bytes()) == a['digest']
    with zipfile.ZipFile(path) as z:
        assert indexed[a['name']] == {n: sha(z.read(n)) for n in z.namelist() if not n.endswith('/')}
with zipfile.ZipFile(out / '13999164903.zip') as z:
    junit = ET.fromstring(z.read('results.xml'))
    tests = [{'name': c.get('name'), 'failed': bool(c.findall('failure') or c.findall('error')),
              'message': [f.get('message') for f in c if f.tag in ('failure', 'error')]}
             for c in junit.findall('.//testcase')]
review = read(HERE / 'verification.json')
assert review['status'] == 'REJECTED_OFFICIAL_POWER_PORT_PRECHECK'
assert review['precheck'] == tests and len(tests) == 10 and sum(c['failed'] for c in tests) == 1
assert next(c for c in tests if c['failed']) == {'name': 'Pin check', 'failed': True,
    'message': ['Some ports are missing or have wrong dimensions, see 148 LEF errors above']}
jobs = {j['name']: j for j in read(HERE / 'jobs.json')['jobs']}
assert jobs['gds']['conclusion'] == 'success' and jobs['precheck']['conclusion'] == 'failure'
raw = (out / 'precheck-job.log').read_bytes()
assert sha(raw) == review['precheck_log_sha256']
submission = next(a for a in artifacts if a['name'] == 'tt_submission')
text = raw.decode()
assert f'- tt_submission (ID: {submission["id"]}, Size: {submission["size_in_bytes"]}, Expected Digest: {submission["digest"]})' in text
assert 'SHA256 digest of downloaded artifact is ' + review['consumed_submission_sha256'] in text
assert 'Artifact download completed successfully.' in text and 'Precheck failed for ' in text
result = subprocess.run([sys.executable, str(HERE / 'audit.py'), '--directory', str(out),
    '--output', str(out / 'qualification-rejection')], cwd=ROOT, capture_output=True)
(out / 'qualification-rejection.log').write_bytes(result.stdout + result.stderr)
assert result.returncode != 0 and read(out / 'qualification-rejection/result.json')['status'] == 'NOT_QUALIFIED'
assert review['original_archive_members'] == sum(len(v) for v in indexed.values()) == 1216
print('PASS_REPLAY_1216_ORIGINAL_FILES_52_PRODUCING_INPUTS_WITH_PIN_REJECTION')
