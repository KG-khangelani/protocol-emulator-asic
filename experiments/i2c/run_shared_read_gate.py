# SPDX-License-Identifier: Apache-2.0
"""D39 reproducible qualification, with strict source identity at every stage."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from shared_read import build, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate', choices=('selection', 'proof-controls'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    manifest = build(out / 'variants')
    result = {'status': 'RUNNING', 'gate': args.gate, 'implementation': 'od128-shared',
              'sources': manifest, 'physical': 'NOT_EVALUATED', 'production': 'UNCHANGED'}

    def save():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    def run(script, subdir, expected, *options):
        subprocess.run([sys.executable, str(ROOT / 'experiments/i2c' / script),
                        '--output', str(out / subdir), *map(str, options)], cwd=ROOT, check=True)
        stage = json.loads((out / subdir / 'result.json').read_bytes())
        assert stage['status'] == expected
        return stage

    save()
    try:
        run('lint_store_lanes.py', 'style', 'PASS_SCOPED_STYLE_REVIEW', '--variants', out / 'variants',
            '--source-revision', 'shared-read')
        if args.gate == 'selection':
            stage = run('run_physical_selection.py', 'selection', 'PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS',
                        '--variants', out / 'variants', '--source-revision', 'shared-read')
            assert stage['sources'] == manifest['od128']['source_sha256']
            result['status'] = 'PASS_SHARED_PUBLIC_SELECTION'
        else:
            stage = run('run_shared_read_proof.py', 'proof', 'PASS_RESET_REACHABLE_COMPLETE_CHIP_EQUIVALENCE',
                        '--variants', out / 'variants')
            assert stage['sources']['gate'] == manifest['od128']['source_sha256']
            stage = run('run_shared_read_controls.py', 'controls', 'PASS_PUBLIC_SHARED_READ_MUTATION_CONTROLS')
            assert stage['sources'] == manifest['od128']['source_sha256']
            stage = run('falsify_shared_read_audit.py', 'audit', 'PASS_SHARED_AUDIT_NEGATIVE_CONTROLS',
                        '--proof', out / 'proof', '--controls', out / 'controls')
            assert stage['sources'] == manifest['od128']['source_sha256']
            result['status'] = 'PASS_SHARED_CHIP_PROOF_AND_CONTROLS'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
