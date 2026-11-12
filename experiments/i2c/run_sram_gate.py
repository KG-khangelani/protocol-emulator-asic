# SPDX-License-Identifier: Apache-2.0
"""Fresh-checkout SRAM qualification; retain exact inputs and bounded outcomes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_sram_candidate import build
from run_current_regression import INPUTS
from sram_prefetch import ROOT, digest

sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from run_program_sensitivity import execute


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--gate', required=True, choices=('proof-controls', 'icarus', 'verilator'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    (out / 'inputs').mkdir(parents=True)
    names = set(INPUTS) | {
        'experiments/i2c/run_sram_gate.py', 'experiments/i2c/build_sram_candidate.py',
        'experiments/i2c/run_prefetch_core_proof.py', 'experiments/i2c/sram_prefetch.py',
        'experiments/i2c/sram_program_store.v', 'experiments/i2c/sram_store_properties.vh',
        'experiments/i2c/run_sram_store_formal.py', 'experiments/i2c/run_sram_store_controls.py',
        'experiments/i2c/run_sram_regression.py', 'experiments/spi_phase/run_program_sensitivity.py',
        'test/sram_program_store.sv', 'docs/specs/g2-sram-prefetch-screen.md',
    }
    inputs = {}
    for name in sorted(names):
        raw = (ROOT / name).read_bytes()
        inputs[name] = digest(raw)
        path = out / 'inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    candidate = out / 'candidate'
    manifest = build(candidate)
    result = {'status': 'RUNNING', 'gate': args.gate, 'candidate': manifest,
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'inputs': inputs, 'stages': {}, 'physical': 'NOT_EVALUATED'}

    def save():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    save()
    commands = {
        'engine': (['run_prefetch_core_proof.py', '--output', str(out / 'engine')], 240,
                   'PASS_COMPOSITIONAL_NEXT_STATE_ENGINE_EQUIVALENCE'),
        'store-controls': (['run_sram_store_controls.py', '--candidate', str(candidate), '--output', str(out / 'store-controls')], 600,
                           'PASS_SRAM_STORE_PORTS_AND_FOUR_CHECKED_CONTROLS'),
        'store-formal': (['run_sram_store_formal.py', '--candidate', str(candidate), '--output', str(out / 'store-formal')], 1000,
                         'PASS_ARBITRARY_LOGICAL_STORE_AND_REAL_MODEL_CONTROL'),
        'regression': (['run_sram_regression.py', '--candidate', str(candidate), '--output', str(out / 'regression'),
                        '--simulator', args.gate], 1900, 'PASS_SRAM_CURRENT_SIMULATOR'),
    }
    selected = ('engine', 'store-controls', 'store-formal') if args.gate == 'proof-controls' else ('regression',)
    try:
        for name in selected:
            argv, limit, expected = commands[name]
            argv[0] = str(ROOT / 'experiments/i2c' / argv[0])
            item = execute([sys.executable, *argv], out / (name + '.log'), limit)
            result['stages'][name] = item
            save()
            assert item['returncode'] == 0 and not item['timed_out'], name
            child = json.loads((out / name / 'result.json').read_bytes())
            assert child['status'] == expected, (name, child['status'])
            if 'candidate' in child:
                assert child['candidate'] == manifest
        assert {n: digest((ROOT / n).read_bytes()) for n in inputs} == inputs
        assert {n: digest((candidate / 'src' / n).read_bytes()) for n in manifest['source_sha256']} == manifest['source_sha256']
        result['status'] = 'PASS_SRAM_GATE'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], args.gate, flush=True)


if __name__ == '__main__':
    main()
