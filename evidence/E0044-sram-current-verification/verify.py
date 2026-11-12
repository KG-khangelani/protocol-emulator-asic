# SPDX-License-Identifier: Apache-2.0
"""Replay exact SRAM preparation artifacts while preserving incomplete gates."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    index, manifest = read(HERE / 'archive.json'), read(HERE / 'manifest.json')
    packed = (HERE / 'verification.tar.gz').read_bytes()
    assert len(packed) == index['bytes'] and sha(packed) == index['sha256']
    with tarfile.open(HERE / 'verification.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            target = (out / member.name).resolve()
            assert member.isfile() and target.is_relative_to(out)
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    for label, wanted in [('inputs', manifest['verification_inputs']),
                          ('normal-inputs', read(out / 'normal/receipts/formal.json')['verification_inputs'])]:
        actual = {p.relative_to(out / label).as_posix(): sha(p.read_bytes())
                  for p in (out / label).rglob('*') if p.is_file()}
        assert actual == wanted
    sys.path.insert(0, str(out / 'inputs'))
    sys.path.insert(0, str(out / 'inputs/tools'))
    from current_run import semantic_check, retained_files
    from current_profile import describe
    from current_sram import audit_current_formal, audit_formal, audit_prediction
    normal = out / 'normal/runs' / manifest['formal_run']
    profile = describe(normal / 'candidate/src')
    assert profile == manifest['profile']
    fast = {}
    for action in ('lint', 'synth', 'smoke'):
        receipt = read(out / 'fast/receipts' / (action + '.json'))
        path = out / 'fast/runs' / Path(receipt['directory']).name
        assert receipt['status'] == 'PASS' and receipt['profile'] == profile
        assert retained_files(path) == receipt['artifact_sha256']
        fast[action] = semantic_check(action, path, profile)
        assert fast[action] == receipt['summary']
    current = audit_current_formal(normal, profile)
    receipt = read(out / 'normal/receipts/formal.json')
    assert receipt['status'] == 'FAILED_OR_INCOMPLETE' and not (out / 'normal/evidence.json').exists()
    assert [c['returncode'] for c in receipt['commands']] == [0, 1]
    legacy = read(normal / 'legacy/result.json')
    assert legacy['status'] == 'FAILED_OR_INCOMPLETE' and 'timed out after' in legacy['error']
    assert '299.999' in legacy['error'] and not legacy['tasks']
    assert not (normal / 'legacy/m1_engine-prove/status').exists()
    try:
        audit_formal(normal, profile)
    except AssertionError:
        pass
    else:
        raise AssertionError('historical timeout accepted as complete formal')
    prediction = audit_prediction(out / 'prediction', profile['source_sha256'])
    first, second = (read(out / label / 'result.json') for label in ('preparation-01', 'preparation-02'))
    assert first['status'] == second['status'] == 'FAILED_OR_INCOMPLETE'
    assert first['error'] == 'instructions' and second['error'] == 'm1_public_readout'
    assert len(first['units']) == 0 and len(second['units']) == 4
    assert read(out / 'preparation-02/instructions/result.json')['status'] == 'PASS_SCOPED_INSTRUCTION_PROOFS'
    assert 'derived clocks are only supported' in (out / 'preparation-02/m1_public_readout.log').read_text()
    flat = out / 'flat-readout'
    assert read(flat / 'result.json')['returncode'] == 0 and not read(flat / 'result.json')['timed_out']
    assert (flat / 'proof/status').read_text().split()[0] == 'PASS'
    assert 'successful proof by k-induction' in (flat / 'run.log').read_text()
    assert (flat / 'before.sby').read_text().replace(
        'prep -top tt_um_khangelani_protocol_emulator',
        'prep -top tt_um_khangelani_protocol_emulator -flatten') == (flat / 'proof.sby').read_text()
    runtime = {}
    for path in sorted((out / 'runtime').glob('*.json')):
        record = read(path)
        assert record['image_id'] == record['configured_image'] == 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
        assert record['state'] == 'exited'
        runtime[record['name']] = record['exit_code']
    assert runtime['g2-sram-current-normal-formal-01'] == 2
    assert runtime['g2-sram-current-formal-probe-01'] == runtime['g2-sram-current-formal-probe-02'] == 1
    assert all(code == 0 for name, code in runtime.items() if name not in (
        'g2-sram-current-normal-formal-01', 'g2-sram-current-formal-probe-01', 'g2-sram-current-formal-probe-02'))
    for name in ('g2-sram-current-repo-check-01', 'g2-sram-current-repo-check-02'):
        log = (out / 'logs' / (name + '.log')).read_text()
        assert 'RESULT: PASS' in log and 'FAILED' not in log
        assert sum(map(int, re.findall(r'Ran (\d+) tests?', log))) == 116
    result = {'status': 'PASS_RETAINED_CURRENT_SRAM_PREPARATION_AND_EXPLICIT_INCOMPLETE_GATES',
              'files': len(index['files']), 'profile': profile, 'fast_stages': fast, 'current_formal': current,
              'prefetch_prediction': prediction, 'repository_checks': 116,
              'historical_timeout_seconds': 300, 'normal_aggregate': 'NOT_PASSED',
              'preparation_failures': 2, 'runtime_exit_codes': runtime, 'production': 'NOT_PROMOTED'}
    (out / 'replay-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], result['files'])


if __name__ == '__main__':
    main()
