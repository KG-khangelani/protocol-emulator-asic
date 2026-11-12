# SPDX-License-Identifier: Apache-2.0
"""Check every retained byte, then replay semantic audits with frozen input code."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    index = json.loads((HERE / 'archives.json').read_bytes())
    assert set(index) == {'pipeline', 'inputs', 'legacy-regression', 'formal-success'}
    count = 0
    for label, entry in index.items():
        packed = HERE / (label + '.tar.gz')
        assert hashlib.sha256(packed.read_bytes()).hexdigest() == entry['archive_sha256']
        target = out / label
        with tarfile.open(packed) as archive:
            members = archive.getmembers()
            assert len(members) == len(entry['files']) and {m.name for m in members} == set(entry['files'])
            for member in members:
                assert member.isfile()
                path = (target / member.name).resolve()
                assert path.is_relative_to(target.resolve())
                raw = archive.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest() == entry['files'][member.name]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                count += 1
    subprocess.run([sys.executable, str(HERE / 'replay.py'), '--directory', str(out),
                    '--manifest', str(HERE / 'manifest.json')], cwd=ROOT, check=True)
    print('PASS:', count, 'exact archived files; seven passing stages, retained formal timeout, earlier formal success and historical regression audited')


if __name__ == '__main__':
    main()
