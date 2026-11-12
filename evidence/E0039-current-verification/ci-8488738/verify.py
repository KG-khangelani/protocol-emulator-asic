# SPDX-License-Identifier: Apache-2.0
"""Replay the original current-command CI archive with its frozen audit inputs."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to((ROOT/'build').resolve())
out.mkdir(parents=True)
for line in (HERE/'SHA256SUMS').read_text().splitlines():
    expected,name=line.split('  ',1)
    assert sha((HERE/name).read_bytes())==expected,name
index=json.loads((HERE/'archives.json').read_bytes())
for key,filename in [('original_zip','current-candidate.zip'),('inputs','inputs.tar.gz')]:
    raw=(HERE/filename).read_bytes()
    assert sha(raw)==index[key]['sha256'] and len(raw)==index[key]['bytes']
target=out/'pipeline'
with zipfile.ZipFile(HERE/'current-candidate.zip') as archive:
    entries=archive.infolist()
    assert archive.testzip() is None and len({e.filename for e in entries})==len(entries)
    assert {e.filename for e in entries if not e.is_dir()}==set(index['original_zip']['files'])
    for entry in entries:
        if entry.is_dir():
            continue
        path=(target/entry.filename).resolve()
        assert path.is_relative_to(target.resolve())
        raw=archive.read(entry)
        assert sha(raw)==index['original_zip']['files'][entry.filename]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
target=out/'inputs'
with tarfile.open(HERE/'inputs.tar.gz') as archive:
    entries=archive.getmembers()
    assert len(entries)==len(index['inputs']['files']) and {e.name for e in entries}==set(index['inputs']['files'])
    for entry in entries:
        path=(target/entry.name).resolve()
        assert entry.isfile() and path.is_relative_to(target.resolve())
        raw=archive.extractfile(entry).read()
        assert sha(raw)==index['inputs']['files'][entry.name]
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
for name in ('artifacts.json','jobs.json'):
    (out/name).write_bytes((HERE/name).read_bytes())
(out/'current-job.log').write_bytes(gzip.decompress((HERE/'current-job.log.gz').read_bytes()))
subprocess.run([sys.executable,str(HERE/'audit.py'),'--directory',str(out)],check=True,cwd=ROOT)
assert json.loads((out/'verification.json').read_bytes())==json.loads((HERE/'verification.json').read_bytes())
print('PASS: original CI ZIP, 250 exact inputs and all eight stages audited; no physical qualification')
