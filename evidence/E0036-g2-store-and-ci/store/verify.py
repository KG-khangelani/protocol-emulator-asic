# SPDX-License-Identifier: Apache-2.0
"""Unpack and independently audit the retained G2 memory-proof inputs/results."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'experiments/i2c'))
from audit_store_proofs import audit


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((ROOT/'build').resolve()) and not out.exists(), 'use a new build directory'
    out.mkdir(parents=True)
    manifest = json.loads((HERE/'archives.json').read_bytes())
    for name, entry in manifest.items():
        source = HERE/(name+'.tar.gz')
        assert digest(source.read_bytes()) == entry['archive_sha256']
        target = out/name
        with tarfile.open(source) as archive:
            members = archive.getmembers()
            assert len(members) == len(entry['files'])
            assert {m.name for m in members} == set(entry['files'])
            for member in members:
                dest = (target/member.name).resolve()
                assert member.isfile() and dest.is_relative_to(target.resolve())
                data = archive.extractfile(member).read()
                assert digest(data) == entry['files'][member.name]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        # Restore only duplicate SBY source copies, using retained originals.
        result = json.loads((target/'result.json').read_bytes())
        for task in result['tasks']:
            directory = target/task['directory']
            dest = directory/'proof/src'
            dest.mkdir(parents=True, exist_ok=True)
            if task['name'] in ('state','read'):
                shutil.copyfile(target/(task['variant']+'-model')/'prepared.il', dest/'prepared.il')
            else:
                shutil.copyfile(directory/'store.v', dest/'store.v')
    positive, controls = out/'i2c-store-local-06', out/'i2c-store-local-07'
    assert digest((positive/'runner.py').read_bytes()) == json.loads((positive/'result.json').read_bytes())['runner_sha256']
    for variant in ('od128','literal255'):
        expected = json.loads((HERE/(variant+'.json')).read_bytes())
        checkpoint = gzip.decompress((HERE/expected['positive_checkpoint']).read_bytes())
        observed = audit(positive, controls, variant, checkpoint)
        assert observed == {k:v for k,v in expected.items() if k != 'positive_checkpoint'}
        print(variant, observed['status'], observed['assertions'], 'assertions')
    print('PASS: archive hashes, every retained byte, models, all proofs and corrected controls')


if __name__ == '__main__':
    main()
