# SPDX-License-Identifier: Apache-2.0
"""Audit retained results using the exact verification code that produced them."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    out, manifest = args.directory.resolve(), read(args.manifest)
    inputs = out / 'inputs'
    sys.path.insert(0, str(inputs / 'tools'))
    sys.path.insert(0, str(inputs))
    from current_run import STAGES, retained_files, semantic_check
    from current_profile import describe
    from run_current_regression import REQUIRED
    profile = describe(inputs / 'evidence/E0038-shared-program-read/sources/od128')
    assert profile == manifest['profile']
    assert not (out / 'pipeline/evidence.json').exists()
    receipts = {action: read(out / 'pipeline/receipts' / (action + '.json')) for action in STAGES}
    expected_inputs = manifest['verification_inputs']
    assert {p.relative_to(inputs).as_posix(): sha(p) for p in inputs.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts} == expected_inputs
    provenance = read(out / 'pipeline/provenance.json')
    assert provenance['status'] == 'PASS' and provenance['profile'] == profile
    assert provenance['verification_inputs'] == expected_inputs
    assert provenance['stages'] == {key: receipts[key] for key in ('rtl-icarus', 'smoke')}
    prefix = PurePosixPath(manifest['pipeline_root'])
    summaries, runtime = {}, None
    for action in STAGES:
        receipt = receipts[action]
        expected_status = 'FAILED_OR_INCOMPLETE' if action == 'formal' else 'PASS'
        assert receipt['schema'] == 'protocol-emulator-current-stage-v1' and receipt['status'] == expected_status
        assert receipt['action'] == action and receipt['profile'] == profile
        assert receipt['verification_inputs'] == expected_inputs
        relative = PurePosixPath(receipt['directory']).relative_to(prefix)
        stage = out / 'pipeline' / relative
        assert stage.resolve().is_relative_to((out / 'pipeline').resolve())
        if action == 'formal':
            assert len(receipt['commands']) == 1 and receipt['commands'][0]['returncode'] != 0
            failed = read(stage / 'current/chip/result.json')
            assert failed['status'] == 'FAILED_OR_INCOMPLETE' and failed['sources']['gate'] == profile['source_sha256']
            temporal = failed['stages']['temporal']
            assert temporal['timed_out'] and temporal['returncode'] == 124 and temporal['wall_limit'] == 300
            summaries[action] = {'status': 'INCOMPLETE_TEMPORAL_PROOF_TIMEOUT', 'seconds': temporal['seconds'], 'wall_limit': 300}
            continue
        assert receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands'])
        assert retained_files(stage) == receipt['artifact_sha256']
        summary = semantic_check(action, stage, profile)
        assert summary == receipt['summary']
        # Parsing a witness must not alter the retained evidence bytes.
        assert retained_files(stage) == receipt['artifact_sha256']
        if action == 'doctor':
            runtime = sha(stage / 'run.log')
            assert 'RESULT: PASS' in (stage / 'run.log').read_text()
        assert receipt['runtime_identity'] == runtime
        summaries[action] = summary
    successful_formal = semantic_check('formal', out / 'formal-success', profile)
    old_instructions = read(out / 'formal-success/current/instructions/result.json')
    assert sha(out / 'formal-success/original-run-general-formal.py') == old_instructions['runner_sha256']
    legacy = read(out / 'legacy-regression/result.json')
    assert legacy['status'] == 'PASS_HISTORICAL_DEFAULT_SUITE_BOTH_SIMULATORS'
    assert legacy['sources'] == describe(inputs / 'experiments/spi_phase/baseline')['source_sha256']
    expected_legacy = {(module, name) for module, name in REQUIRED
                       if module in ('test', 'test_uart_rx_public', 'test_spi_mode0_public')}
    assert len(expected_legacy) == 22
    assert [s['simulator'] for s in legacy['stages']] == ['icarus', 'verilator']
    for simulator in ('icarus', 'verilator'):
        root = ET.parse(out / 'legacy-regression' / simulator / 'results.xml').getroot()
        cases = root.findall('.//testcase')
        assert len(cases) == 22 and {(c.get('classname'), c.get('name')) for c in cases} == expected_legacy
        assert not any(root.findall('.//' + tag) for tag in ('failure', 'error', 'skipped'))
    # Reproduce the first collector's real cache defect using its frozen code.
    # The fixture changes only a newly extracted, previously unbound metadata file.
    import current_profile
    import current_run
    import learning_status
    control = args.manifest.parent / 'initial-cache-control'
    witness = read(control / 'result.json')
    assert sha(inputs / 'tools/current_run.py') == witness['old_collector_sha256']
    metadata = inputs / witness['metadata']
    assert not metadata.exists()
    metadata.parent.mkdir(parents=True, exist_ok=True)
    names = ('\0'.join([*expected_inputs, witness['metadata']]) + '\0').encode()
    metadata.write_bytes((control / 'original.json').read_bytes())
    with patch.object(current_profile.subprocess, 'check_output', return_value=names):
        before = current_profile.verification_inputs()
        metadata.write_bytes((control / 'corrupted.json').read_bytes())
        after = current_profile.verification_inputs()
    assert before == after == expected_inputs
    translated = dict(receipts['check'])
    translated['directory'] = 'pipeline/' + PurePosixPath(translated['directory']).relative_to(prefix).as_posix()
    (out / 'receipts').mkdir()
    current_run.write(out / 'receipts/check.json', translated)
    with patch.object(current_run, 'ROOT', out):
        assert current_run.load_receipt(out, 'check', profile, after, runtime)['status'] == 'PASS'
    try:
        learning_status.validate(read(metadata))
    except SystemExit as error:
        assert str(error) == witness['fresh_validator_rejection']
    else:
        raise AssertionError('fresh validation must reject the deliberately corrupted metadata')
    metadata.unlink()
    result = {'status': 'PASS_RETAINED_INTEGRATION_EVIDENCE_WITH_INCOMPLETE_COMMAND_RUN', 'profile': profile,
              'stages': summaries, 'historical_regression': {'icarus': 22, 'verilator': 22},
              'separate_successful_formal': successful_formal,
              'input_files': len(expected_inputs), 'initial_cache_gap_reproduced': True,
              'physical': 'NOT_EVALUATED', 'production': 'NOT_PROMOTED'}
    (out / 'verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
