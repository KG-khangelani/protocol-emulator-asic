# SPDX-License-Identifier: Apache-2.0
"""Reject incomplete, corrupt and rehashed wrong program evidence; never edit originals."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda path: json.loads(path.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
write = lambda path, value: path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def execute(output):
    output = output.resolve()
    assert output.is_relative_to((ROOT / 'build').resolve()) and not output.exists()
    baseline = read(HERE / 'verification.json')
    assert baseline['status'] == 'PASS_G4_FRESH_PROGRAM_TOOLCHAIN_CI'
    spec = importlib.util.spec_from_file_location('g4_program_frozen_audit', HERE / 'verify.py')
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    assert audit.audit(HERE) == baseline
    output.mkdir(parents=True)
    names = [str(a['id']) + '.zip' for a in baseline['artifacts'].values()]
    cases = [
        ('unfinished-workflow', None, 'program-tools workflow is incomplete'),
        ('wrong-archive-digest', None, 'original archive digest differs'),
        ('rehashed-skipped-group', 'icarus/results.xml', 'required public group failed or skipped'),
        ('rehashed-program-binary', 'examples/uart_tx/program.bin', 'compiled binary differs from catalog'),
        ('rehashed-producing-input', 'result.json', 'producing input set differs'),
    ]
    results = []
    for label, member, expected in cases:
        directory = output / label
        directory.mkdir()
        run, jobs, artifacts = (read(HERE / name) for name in ('run.json', 'jobs.json', 'artifacts.json'))
        public = next(a for a in artifacts['artifacts'] if a['id'] == baseline['artifacts']['public']['id'])
        target_name = str(public['id']) + '.zip'
        for name in names:
            if member and name == target_name:
                continue
            os.link(HERE / name, directory / name)
        logs = {kind: gzip.decompress((HERE / (kind + '-job.log.gz')).read_bytes())
                for kind in ('public', 'windows')}
        mutation = None
        if label == 'unfinished-workflow':
            run.update(status='in_progress', conclusion=None)
        elif label == 'wrong-archive-digest':
            public['digest'] = 'sha256:' + '0' * 64
        else:
            with zipfile.ZipFile(HERE / target_name) as original, zipfile.ZipFile(directory / target_name, 'w') as target:
                before = original.read(member)
                if label == 'rehashed-skipped-group':
                    root = ET.fromstring(before)
                    selected = root.find('.//testcase[@name="assembled_i2c_examples"]')
                    assert selected is not None and not list(selected)
                    ET.SubElement(selected, 'skipped')
                    after = ET.tostring(root)
                elif label == 'rehashed-program-binary':
                    after = bytes([before[0] ^ 1]) + before[1:]
                else:
                    data = json.loads(before)
                    data['inputs_sha256']['tools/assembler.py'] = '0' * 64
                    after = (json.dumps(data, indent=2, sort_keys=True) + '\n').encode()
                for entry in original.infolist():
                    target.writestr(entry, after if entry.filename == member else original.read(entry.filename))
            raw = (directory / target_name).read_bytes()
            old_digest = public['digest'].removeprefix('sha256:')
            new_digest = sha(raw)
            public.update(size_in_bytes=len(raw), digest='sha256:' + new_digest)
            # Synthetic upload log alteration deliberately gets past transport checks.
            # It is retained as an explicit fault, never represented as a real CI log.
            assert old_digest.encode() in logs['public']
            logs['public'] = logs['public'].replace(old_digest.encode(), new_digest.encode())
            mutation = {'archive': 'public', 'member': member,
                        'before_sha256': sha(before), 'after_sha256': sha(after),
                        'synthetic_archive_sha256': new_digest,
                        'api_and_upload_log_deliberately_rehashed': True}
        for name, value in (('run.json', run), ('jobs.json', jobs), ('artifacts.json', artifacts)):
            write(directory / name, value)
        for kind, raw in logs.items():
            (directory / (kind + '-job.log.gz')).write_bytes(gzip.compress(raw, mtime=0))
        try:
            audit.audit(directory)
        except AssertionError as error:
            observed = str(error)
        else:
            raise AssertionError('Corrupt evidence was accepted: ' + label)
        assert observed == expected, (label, observed, expected)
        result = {'case': label, 'status': 'PASS_REJECTED_CORRUPTION', 'expected_error': expected,
                  'observed_error': observed, 'mutation': mutation}
        write(directory / 'result.json', result)
        results.append(result)
        print('PASS_REJECTED_CORRUPTION', label, flush=True)
    result = {'schema': 'protocol-emulator-g4-program-audit-controls-v1',
              'status': 'PASS_FIVE_G4_PROGRAM_EVIDENCE_CONTROLS',
              'baseline_verification_sha256': sha((HERE / 'verification.json').read_bytes()),
              'audit_sha256': sha((HERE / 'verify.py').read_bytes()),
              'runner_sha256': sha(Path(__file__).read_bytes()), 'cases': results,
              'scope': 'Synthetic incomplete and altered archive controls; no fresh hardware simulation.'}
    write(output / 'result.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(execute(args.output)['status'])
