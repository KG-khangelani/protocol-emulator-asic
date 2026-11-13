# SPDX-License-Identifier: Apache-2.0
"""Reconstruct original archives and replay the complete qualification audit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--controls', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
out.mkdir(parents=True)
storage = read(HERE / 'storage.json')
for name, parts in storage.items():
    assert '/' not in name and '\\' not in name and name.endswith('.zip')
    with (out / name).open('wb') as target:
        for part in parts:
            raw = (HERE / part['name']).read_bytes()
            assert len(raw) == part['bytes'] and sha(raw) == part['sha256']
            target.write(raw)
for name in ('run.json', 'jobs.json', 'artifacts.json'):
    (out / name).write_bytes((HERE / name).read_bytes())
for name in ('gds', 'precheck', 'gl_test'):
    (out / (name + '-job.log')).write_bytes(gzip.decompress((HERE / (name + '-job.log.gz')).read_bytes()))
indexed = read(HERE / 'zip-files.json')
for a in read(HERE / 'artifacts.json')['artifacts']:
    if a['name'] not in indexed:
        continue
    path = out / (str(a['id']) + '.zip')
    assert path.stat().st_size == a['size_in_bytes'] and 'sha256:' + sha(path.read_bytes()) == a['digest']
    with zipfile.ZipFile(path) as z:
        assert indexed[a['name']] == {n:sha(z.read(n)) for n in z.namelist() if not n.endswith('/')}
subprocess.run([sys.executable, str(HERE / 'audit.py'), '--directory', str(out),
    '--output', str(out / 'audit')], cwd=ROOT, check=True)
result = read(out / 'audit/result.json')
assert result == read(HERE / 'result.json')
producer = read(HERE / 'producer.json')
assert producer['files'] == {p.relative_to(out / 'audit/producer').as_posix(): sha(p.read_bytes())
    for p in (out / 'audit/producer').rglob('*') if p.is_file()}
if args.controls:
    subprocess.run([sys.executable, str(HERE / 'controls.py'), '--base', str(out),
        '--audit', str(HERE / 'audit.py'), '--output', str(out / 'controls')], cwd=ROOT, check=True)
verification = {'status': 'PASS_RETAINED_COMPLETE_SRAM_QUALIFICATION', 'source_commit': result['source_commit'],
    'run_id': result['run_id'], 'original_archive_files': sum(map(len, indexed.values())),
    'producing_inputs': len(producer['files']), 'gds_sha256': result['gds_sha256'],
    'netlist_sha256': result['netlist_sha256'], 'controls_executed': args.controls}
(out / 'verification.json').write_bytes((json.dumps(verification, indent=2) + '\n').encode())
print(verification['status'], verification['original_archive_files'], verification['producing_inputs'])
