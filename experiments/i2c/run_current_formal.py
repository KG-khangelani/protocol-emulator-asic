# SPDX-License-Identifier: Apache-2.0
"""Source-bound current-chip proof, instruction controls and support-unit properties."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import physical_g2 as physical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    out.mkdir(parents=True)
    original = args.sources.resolve()
    hashes = physical.verify_sources(original, 'od128-shared')
    variants = out / 'variants'
    sources = variants / 'od128/src'
    sources.mkdir(parents=True)
    for name in hashes:
        (sources / name).write_bytes((original / name).read_bytes())
    manifest = physical.read_json(physical.shared_read.MANIFEST)
    physical.write_json(variants / 'source-manifest.json', manifest)
    result = {'status': 'RUNNING', 'source_directory': str(original), 'sources': hashes, 'stages': [],
              'scope': 'Current complete-chip equivalence/reset, current generic-instruction properties/controls, actual data store/synchronizer/public readout and host deadline lemma. Historical engine/store assertions are a separate baseline profile.'}

    def save():
        physical.write_json(out / 'result.json', result)

    def run(label, command, timeout=600):
        start = time.monotonic()
        with (out / (label + '.log')).open('w') as log:
            proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        result['stages'].append({'name': label, 'command': command, 'returncode': proc.returncode,
                                 'seconds': round(time.monotonic()-start, 3), 'log_sha256': physical.digest(out / (label + '.log'))})
        save()
        assert proc.returncode == 0, label

    save()
    try:
        run('complete-chip', [sys.executable, str(ROOT / 'experiments/i2c/run_shared_read_proof.py'),
                             '--variants', str(variants), '--output', str(out / 'chip')])
        chip = physical.read_json(out / 'chip/result.json')
        assert chip['status'] == 'PASS_RESET_REACHABLE_COMPLETE_CHIP_EQUIVALENCE' and chip['sources']['gate'] == hashes
        run('instructions', [sys.executable, str(ROOT / 'experiments/i2c/run_general_formal.py'),
                             '--variants', str(variants), '--variant', 'od128', '--output', str(out / 'instructions')])
        instructions = physical.read_json(out / 'instructions/result.json')
        assert instructions['status'] == 'PASS_SCOPED_INSTRUCTION_PROOFS'
        assert instructions['sources'] == {'od128': hashes['m1_engine.v']}
        assert len(instructions['tasks']) == 4 and all(t['accepted'] for t in instructions['tasks'])
        units = []
        for filename, tasks in (('m1_data_store', ('prove', 'cover')), ('m1_input_sync', ('prove', 'cover')),
                                ('m1_public_readout', (None,))):
            raw = (ROOT / 'formal' / (filename + '.sby')).read_text()
            script, files = raw.split('[files]\n')
            inputs = []
            for name in files.splitlines():
                if not name.strip():
                    continue
                source = sources / Path(name).name if name.startswith('src/') else ROOT / name
                assert source.is_file()
                inputs.append(source)
            config = out / (filename + '.sby')
            config.write_text(script + '[files]\n' + '\n'.join(str(p) for p in inputs) + '\n')
            for task in tasks:
                name = filename + ('-' + task if task else '')
                directory = out / name
                run(name, ['sby', '-f', '-d', str(directory), str(config)] + ([task] if task else []), 300)
                status = (directory / 'status').read_text().split()[0]
                assert status == 'PASS', name
                log = (out / (name + '.log')).read_text()
                if task != 'cover':
                    assert 'successful proof by k-induction' in log, name
                witnesses = {p.relative_to(directory).as_posix(): physical.digest(p)
                             for p in directory.glob('engine_*/trace*.vcd')}
                if task == 'cover':
                    assert witnesses, name
                # Verify the sources actually copied into the solver workspace.
                for source in inputs:
                    assert (directory / 'src' / source.name).read_bytes() == source.read_bytes()
                units.append({'name': name, 'status': status, 'inputs': {p.name: physical.digest(p) for p in inputs},
                              'proof_sby_sha256': physical.digest(config), 'witnesses': witnesses})
        result['units'] = units
        run('host-deadline', [sys.executable, str(ROOT / 'tools/check_host_deadline.py')], 120)
        assert physical.verify_sources(original, 'od128-shared') == hashes
        assert physical.verify_sources(sources, 'od128-shared') == hashes
        result['status'] = 'PASS_CURRENT_CHIP_INSTRUCTION_AND_SUPPORT_FORMAL'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
