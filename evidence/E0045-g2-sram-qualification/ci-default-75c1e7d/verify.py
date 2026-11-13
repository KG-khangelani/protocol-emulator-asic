# SPDX-License-Identifier: Apache-2.0
"""Replay the original actual-default-production CI ZIP using its frozen Linux audit."""
import argparse
import gzip
import hashlib
import json
import os
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
assert os.name == 'posix', 'Run this frozen audit in the Linux workbench; its original VCD parser writes native line endings.'
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
out.mkdir(parents=True)
index = json.loads((HERE / 'inputs.json').read_bytes())
packed = (HERE / 'inputs.tar.gz').read_bytes()
assert sha(packed) == index['sha256'] and len(packed) == index['bytes']
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
for name in ('run.json', 'jobs.json', 'artifacts.json', '14009675508.zip'):
    (out / name).write_bytes((HERE / name).read_bytes())
(out / 'current-job.log').write_bytes(gzip.decompress((HERE / 'current-job.log.gz').read_bytes()))
subprocess.run([sys.executable, str(HERE / 'audit.py'), '--directory', str(out)], check=True, cwd=ROOT)
assert json.loads((out / 'verification.json').read_bytes()) == json.loads((HERE / 'verification.json').read_bytes())
assert json.loads((out / 'zip-files.json').read_bytes()) == json.loads((HERE / 'zip-files.json').read_bytes())
print('PASS_RETAINED_DEFAULT_PRODUCTION_CI_1922_FILES_329_INPUTS_ALL_EIGHT_STAGES')
