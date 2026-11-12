# SPDX-License-Identifier: Apache-2.0
"""Preserve the complete original formal suite on its immutable E0020 baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from legacy_baseline import BASELINE, baseline_sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    out.mkdir(parents=True)
    sources = baseline_sources()
    hashes = {n: hashlib.sha256(raw.encode()).hexdigest() for n, raw in sources.items()}
    result = {'status': 'RUNNING', 'sources': hashes, 'tasks': [],
              'scope': 'HISTORICAL_E0020_FORMAL_BASELINE_NOT_CURRENT_CHIP'}

    def save():
        (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())

    save()
    try:
        for filename, tasks in (('m1_engine', ('prove', 'cover')), ('m1_engine_mutation', (None,)),
                                ('m1_program_store', ('prove', 'cover')), ('m1_data_store', ('prove', 'cover')),
                                ('m1_input_sync', ('prove', 'cover')), ('m1_public_readout', (None,))):
            raw = (ROOT / 'formal' / (filename + '.sby')).read_text()
            script, entries = raw.split('[files]\n')
            inputs = [(BASELINE / Path(n).name if n.startswith('src/') else ROOT / n)
                      for n in entries.splitlines() if n.strip()]
            config = out / (filename + '.sby')
            config.write_text(script + '[files]\n' + '\n'.join(str(p) for p in inputs) + '\n')
            for task in tasks:
                name = filename + ('-' + task if task else '')
                directory = out / name
                command = ['sby', '-f', '-d', str(directory), str(config)] + ([task] if task else [])
                start = time.monotonic()
                with (out / (name + '.log')).open('w') as log:
                    proc = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300)
                status = (directory / 'status').read_text().split()[0] if (directory / 'status').exists() else 'MISSING'
                expected = 'FAIL' if filename == 'm1_engine_mutation' else 'PASS'
                text = (out / (name + '.log')).read_text()
                accepted = proc.returncode == 0 and status == expected
                if expected == 'PASS' and task != 'cover':
                    accepted &= 'successful proof by k-induction' in text
                witnesses = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in directory.glob('engine_*/trace*.vcd')}
                if task == 'cover' or expected == 'FAIL':
                    accepted &= bool(witnesses)
                assert all((directory / 'src' / p.name).read_bytes() == p.read_bytes() for p in inputs)
                result['tasks'].append({'name': name, 'command': command, 'returncode': proc.returncode,
                    'status': status, 'expected': expected, 'accepted': bool(accepted),
                    'seconds': round(time.monotonic()-start, 3), 'witnesses': witnesses,
                    'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}})
                save()
                assert accepted, name
        assert baseline_sources() == sources
        assert len(result['tasks']) == 10
        result['status'] = 'PASS_COMPLETE_HISTORICAL_FORMAL_BASELINE'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
