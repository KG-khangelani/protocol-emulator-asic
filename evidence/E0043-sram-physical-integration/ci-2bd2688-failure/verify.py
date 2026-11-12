# SPDX-License-Identifier: Apache-2.0
"""Recheck both original rejected CI archives and their frozen source/runtime audit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
out.mkdir(parents=True)
index = json.loads((HERE / 'inputs.json').read_bytes())
raw = (HERE / 'inputs.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'inputs.tar.gz') as archive:
    entries = archive.getmembers()
    assert len(entries) == len(index['files']) and {e.name for e in entries} == set(index['files'])
    for entry in entries:
        path = (out / 'inputs' / entry.name).resolve()
        assert entry.isfile() and path.is_relative_to(out / 'inputs')
        raw = archive.extractfile(entry).read()
        assert sha(raw) == index['files'][entry.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
for name in ('13986867590.zip', '13985889229.zip', 'run.json', 'jobs.json', 'artifacts.json', 'mapped-input-observation.json'):
    (out / name).write_bytes((HERE / name).read_bytes())
(out / 'gds-job.log').write_bytes(gzip.decompress((HERE / 'gds-job.log.gz').read_bytes()))
subprocess.run([sys.executable, str(HERE / 'audit.py'), str(out)], check=True, cwd=ROOT)
for name in ('verification.json', 'zip-files.json'):
    assert json.loads((out / name).read_bytes()) == json.loads((HERE / name).read_bytes())
print('PASS_REPLAY_OF_REJECTED_OFFICIAL_SRAM_RUN_961_ORIGINAL_FILES')
