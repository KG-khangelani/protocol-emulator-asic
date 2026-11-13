# SPDX-License-Identifier: Apache-2.0
"""Replay the rejected official archive audit, optionally its native geometry audit."""
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
read = lambda path: json.loads(path.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--native', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
out.mkdir(parents=True)
for label in ('inputs', 'geometry-inputs'):
    index = read(HERE / (label + '.json'))
    raw = (HERE / (label + '.tar.gz')).read_bytes()
    assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
    with tarfile.open(HERE / (label + '.tar.gz')) as archive:
        entries = archive.getmembers()
        assert len(entries) == len(index['files']) and {e.name for e in entries} == set(index['files'])
        for entry in entries:
            path = (out / label / entry.name).resolve()
            assert entry.isfile() and path.is_relative_to(out / label)
            raw = archive.extractfile(entry).read()
            assert sha(raw) == index['files'][entry.name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
for name in ('13994632526.zip', '13994288135.zip', 'run.json', 'jobs.json', 'artifacts.json', 'mapped-input-observation.json'):
    (out / name).write_bytes((HERE / name).read_bytes())
(out / 'gds-job.log').write_bytes(gzip.decompress((HERE / 'gds-job.log.gz').read_bytes()))
subprocess.run([sys.executable, str(HERE / 'audit.py'), str(out)], check=True, cwd=ROOT)
for name in ('verification.json', 'zip-files.json'):
    assert read(out / name) == read(HERE / name)
geometry = read(HERE / 'contact-geometry.json')
assert geometry['status'] == 'PASS_ALL_36_OFFICIAL_MARKERS_MATCH_32_ISOLATED_FOOTPRINTS'
assert len(geometry['observations']) == 36 and geometry['unique_contact_count'] == 32
assert geometry['marker_footprint_xor'] == 'EMPTY' and geometry['official_local_shape_xor'] == 'EMPTY_ALL_LAYERS'
assert len(geometry['official_local_shape_xor_layers']) == 28
assert geometry['gds_sha256'] == read(HERE / 'verification.json')['checked_gds_sha256']
for observation in geometry['observations']:
    assert observation['minimum_activ_enclosure_nm'] >= observation['reference_limit_nm']
if args.native:
    subprocess.run([sys.executable, str(HERE / 'replay_geometry.py'), str(out)], check=True, cwd=ROOT)
    assert read(out / 'contact-geometry.json') == geometry
print('PASS_REJECTED_GUARDED_RUN_1027_ORIGINAL_FILES_42_FROZEN_INPUTS', 'NATIVE_GEOMETRY' if args.native else 'ARCHIVE_AUDIT')
