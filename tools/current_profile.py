# SPDX-License-Identifier: Apache-2.0
"""Identify the actual source profile; an unknown source never falls back to legacy."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from legacy_baseline import FILES, baseline_sources


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(directory=None):
    directory = Path(directory or ROOT / 'src').resolve()
    actual = {n: digest(directory / n) for n in FILES}
    old = {n: hashlib.sha256(raw.encode()).hexdigest() for n, raw in baseline_sources().items()}
    if actual == old:
        return {'profile': 'legacy8', 'source_sha256': actual, 'program_words': 8, 'pc_bits': 5}
    path = ROOT / 'evidence/E0038-shared-program-read/sources/source-manifest.json'
    current = json.loads(path.read_bytes())['od128']['source_sha256']
    if actual == current:
        return {'profile': 'od128-shared', 'source_sha256': actual, 'program_words': 128, 'pc_bits': 8}
    sram = json.loads((ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json').read_bytes())
    if actual == sram['source_sha256']:
        return {'profile': 'od128-sram', 'source_sha256': actual, 'program_words': 128, 'pc_bits': 8,
                'interface_id': '0x22', 'physical_memory_bits': 8192, 'model_sha256': sram['model_sha256']}
    raise ValueError('Unrecognized source profile: qualify and declare the changed source before using a production verification profile')


def verification_inputs():
    """Bind code/configuration, frozen proof inputs and the reference observations."""
    names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
    prefixes = ('src/', 'test/', 'tools/', 'formal/', 'experiments/', '.github/workflows/', 'docs/specs/',
                'evidence/E0035-general-i2c/sources/current/', 'evidence/E0037-explicit-store-lanes/sources/',
                'evidence/E0038-shared-program-read/sources/',
                'evidence/E0042-sram-prefetch-screen/feasibility/verilog/')
    singles = {'Makefile', 'info.yaml', '.rules.verible_lint', 'requirements-dev.txt', 'tools/workbench/requirements.lock',
               'evidence/E0020-spi-mode0-feasibility/result.json',
               'evidence/E0037-explicit-store-lanes/qualification.json',
               'evidence/E0038-shared-program-read/qualification.json',
               'evidence/E0038-shared-program-read/verify.py',
               'evidence/E0042-sram-prefetch-screen/candidate.json',
               'evidence/E0042-sram-prefetch-screen/feasibility/inspection.json',
               'evidence/E0042-sram-prefetch-screen/ci-95120d8/proof_checks.py',
               'evidence/E0036-g2-store-and-ci/ci/architecture/combined/icarus/records/cases.jsonl.gz',
               'evidence/E0036-g2-store-and-ci/ci/od128/protocols/icarus/records/cases.jsonl.gz',
               'evidence/E0036-g2-store-and-ci/ci/architecture/boundaries/od128-icarus/records/boundaries.jsonl.gz',
               'evidence/E0036-g2-store-and-ci/ci/architecture/aborts/od128-icarus/records/aborts.jsonl.gz'}
    selected = {n for n in names if n and (n.startswith(prefixes) or n in singles) and (ROOT / n).is_file()}
    assert singles <= selected, 'missing required verification input'
    return {n: digest(ROOT / n) for n in sorted(selected)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path)
    args = parser.parse_args()
    try:
        print(describe(args.sources)['profile'])
    except (OSError, ValueError) as error:
        print('unsupported')
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
