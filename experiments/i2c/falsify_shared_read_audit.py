# SPDX-License-Identifier: Apache-2.0
"""Reject corrupted real proof models and simulated fault witnesses, after rehashing."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil

from shared_read import ROOT, MANIFEST, digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proof', type=Path, required=True)
    parser.add_argument('--controls', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    out.mkdir(parents=True)
    path = ROOT / 'evidence/E0038-shared-program-read/verify.py'
    spec = importlib.util.spec_from_file_location('shared_evidence_audit', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    sources = json.loads(MANIFEST.read_bytes())['od128']['source_sha256']
    proof, controls = out / 'proof', out / 'controls'
    shutil.copytree(args.proof, proof)
    shutil.copytree(args.controls, controls, ignore=shutil.ignore_patterns('sim'))
    assert audit.audit_proof(proof, sources)['actual_state_bits_per_chip'] == 4278
    assert audit.audit_controls(controls, sources)['checked_mutant_counterexamples'] == 6
    original = {p: p.read_bytes() for base in (proof, controls) for p in base.rglob('*') if p.is_file()}
    reports = []

    def write(path, data):
        path.write_bytes((json.dumps(data, indent=2) + '\n').encode())

    def model(name, transform):
        path = proof / name
        doc = json.loads(path.read_bytes())
        transform(next(iter(doc['modules'].values())))
        write(path, doc)
        result = json.loads((proof / 'result.json').read_bytes())
        result['model_sha256'][name] = digest(path.read_bytes())
        write(proof / 'result.json', result)

    def first_cell(module, kind):
        return next(c for c in module['cells'].values() if c['type'] == kind)

    def drop_state():
        def change(module):
            del module['cells'][next(n for n, c in module['cells'].items() if 'dff' in c['type'].lower())]
        model('gold.json', change)

    def exclude_state():
        (proof / 'blacklist.txt').write_bytes((proof / 'blacklist.txt').read_bytes() + b'store.word127\n')
        result = json.loads((proof / 'result.json').read_bytes())
        result['excluded_combinational_names'].append('store.word127')
        result['model_sha256']['blacklist.txt'] = digest((proof / 'blacklist.txt').read_bytes())
        write(proof / 'result.json', result)

    def missing_control():
        result = json.loads((controls / 'result.json').read_bytes())
        result['stages'].pop()
        write(controls / 'result.json', result)

    def wrong_witness():
        path = controls / 'high-bank-alias/icarus/observations.json'
        doc = json.loads(path.read_bytes())
        doc['reads'][256][2] ^= 1
        write(path, doc)
        result = json.loads((controls / 'result.json').read_bytes())
        next(s for s in result['stages'] if s['control'] == 'high-bank-alias' and s['simulator'] == 'icarus')['observations_sha256'] = digest(path.read_bytes())
        write(controls / 'result.json', result)

    def fake_mutant():
        path = controls / 'high-bank-alias/src/m1_program_store.v'
        path.write_bytes((controls / 'baseline/src/m1_program_store.v').read_bytes())
        result = json.loads((controls / 'result.json').read_bytes())
        for stage in result['stages']:
            if stage['control'] == 'high-bank-alias':
                stage['source_sha256']['m1_program_store.v'] = digest(path.read_bytes())
        write(controls / 'result.json', result)

    cases = [
        ('missing-actual-state', drop_state, 'proof'),
        ('excluded-state-match', exclude_state, 'proof'),
        ('unproven-temporal-bit', lambda: model('after.json', lambda m: first_cell(m, '$equiv')['connections'].update(A=['x'])), 'proof'),
        ('disabled-reset-assertion', lambda: model('reset.json', lambda m: first_cell(m, '$assert')['connections'].update(EN=['0'])), 'proof'),
        ('missing-public-output', lambda: model('before.json', lambda m: m['ports'].pop('uio_oe')), 'proof'),
        ('wrong-reset-premise', lambda: (proof / 'reset.ys').write_bytes((proof / 'reset.ys').read_bytes().replace(b'-set-at 1 rst_n 0', b'-set-at 1 ena 0')), 'proof'),
        ('missing-proof-success', lambda: (proof / 'temporal.log').write_bytes((proof / 'temporal.log').read_bytes().replace(b'Equivalence successfully proven!', b'Equivalence was not established')), 'proof'),
        ('missing-mutant-observation', missing_control, 'controls'),
        ('wrong-public-counterexample', wrong_witness, 'controls'),
        ('unmodified-mutant-source', fake_mutant, 'controls'),
    ]
    for name, mutate, target in cases:
        try:
            mutate()
            changes = {p.relative_to(out).as_posix(): {'before_sha256': digest(raw), 'after_sha256': digest(p.read_bytes())}
                       for p, raw in original.items() if p.read_bytes() != raw}
            assert changes, 'control did not change evidence'
            try:
                (audit.audit_proof if target == 'proof' else audit.audit_controls)(proof if target == 'proof' else controls, sources)
            except (AssertionError, ValueError) as error:
                reports.append({'name': name, 'rejected': True, 'error': type(error).__name__, 'changed_files': changes})
            else:
                raise RuntimeError('audit accepted corrupt evidence: ' + name)
        finally:
            for path, raw in original.items():
                if path.read_bytes() != raw:
                    path.write_bytes(raw)
    result = {'status': 'PASS_SHARED_AUDIT_NEGATIVE_CONTROLS', 'sources': sources, 'controls': reports,
              'baseline_proof_and_controls': 'PASS', 'rehash_policy': 'Update reported hashes for mutated models, observations and source; require semantic rejection, not checksum mismatch alone.'}
    write(out / 'result.json', result)
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
