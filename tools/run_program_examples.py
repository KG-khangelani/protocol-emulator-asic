# SPDX-License-Identifier: Apache-2.0
"""One command to build versioned programs and check actual public-pin execution."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import json_bytes
from tools.program_examples import build
from tools.production_sram import verify
from tools.current_profile import verification_inputs

GROUPS = {'assembled_loader_controls', 'assembled_uart_examples', 'assembled_spi_examples', 'assembled_i2c_examples'}
COUNTS = {'loader': 7, 'uart_tx': 3, 'uart_rx': 2, 'spi': 25, 'i2c': 18}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, directory, label, timeout, env=None):
    log = directory / (label + '.log')
    with log.open('wb') as stream:
        proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise RuntimeError(f'{label} failed ({proc.returncode}); see {log}')
    return {'command': command, 'returncode': proc.returncode, 'log_sha256': digest(log)}


def audit_records(directory):
    records = [json.loads(line) for line in (directory / 'records.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(records) == sum(COUNTS.values())
    assert len({r['name'] for r in records}) == len(records)
    assert {group: sum(r['group'] == group for r in records) for group in COUNTS} == COUNTS
    for row in records:
        raw = gzip.decompress((directory / (row['name'] + '.json.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == row['trace_sha256']
        assert len(json.loads(raw)) == row['observations'] and row['observations'] > 0
        if row['group'] == 'loader':
            if not row['expected_acceptance']:
                assert row['rejected']
        else:
            assert row['accepted'] == row['expected_acceptance'], row
            if row['group'] in ('spi', 'i2c'):
                assert bool(row['errors']) != row['expected_acceptance'], row
    assert sum(not r['expected_acceptance'] for r in records) == 15
    return sorted(records, key=lambda record: record['name'])


def execute(output, simulators, build_only=False):
    output = output.resolve()
    if not output.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('output must be a new directory under the repository build/ directory')
    if output.exists():
        raise ValueError('output exists; choose a fresh --out directory to preserve prior results')
    output.mkdir(parents=True)
    result = {'schema': 'protocol-emulator-program-verification-v1', 'status': 'RUNNING',
              'observed_utc': datetime.now(timezone.utc).isoformat(),
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'stages': []}
    save = lambda: (output / 'result.json').write_bytes(json_bytes(result))
    save()
    try:
        result['production'] = verify(ROOT)
        result['inputs_sha256'] = verification_inputs()
        result['build'] = build(output / 'examples')
        if build_only:
            result['status'] = 'PASS_BUILD_AND_FROZEN_WORDS'
            return result
        strict = dict(os.environ, PROTOCOL_EMULATOR_LOCKED_WORKBENCH='1')
        result['stages'].append(run([sys.executable, 'tools/doctor.py'], output, 'doctor', 120, strict))
        result['stages'].append(run([sys.executable, '-m', 'unittest', 'discover', '-s', 'test', '-p',
                                     'test_program_tools.py'], output, 'unit-tests', 180, strict))
        models = output / 'models'
        models.mkdir()
        for name, expected in result['production']['model_sha256'].items():
            path = ROOT / 'evidence/E0042-sram-prefetch-screen/feasibility/verilog' / (name + '.gz')
            raw = gzip.decompress(path.read_bytes())
            assert hashlib.sha256(raw).hexdigest() == expected
            (models / name).write_bytes(raw)
        observed = {}
        for simulator in simulators:
            stage = output / simulator
            stage.mkdir()
            env = dict(strict)
            for key in ('GATES', 'G1_PHYSICAL', 'G2_PHYSICAL', 'COCOTB_TESTCASE', 'COCOTB_TEST_FILTER',
                        'MAKEFLAGS', 'COMPILE_ARGS', 'LEARNING_VCD', 'M0_LEARNING', 'COCOTB_PLUSARGS',
                        'COCOTB_TEST_MODULES', 'SIM', 'SRC_DIR', 'SIM_BUILD', 'PYTHONPATH'):
                env.pop(key, None)
            env.update(GENERAL_IO='yes', G2_CURRENT='yes', G2_SRAM='yes', SRAM_MODEL_DIR=str(models),
                       G3_PROGRAM_BUILD=str(output / 'examples'), G3_PROGRAM_RECORDS=str(stage / 'records'),
                       COCOTB_RANDOM_SEED='20261113', PYTHONHASHSEED='0')
            command = ['make', '-C', 'test', 'SIM=' + simulator, 'SRC_DIR=' + str(ROOT / 'src'),
                       'SIM_BUILD=' + str(stage / 'sim'), 'COCOTB_TEST_MODULES=test_program_examples_public',
                       'COCOTB_RESULTS_FILE=' + str(stage / 'results.xml'), 'FST=', 'COCOTB_PLUSARGS=+NO_DUMP']
            result['stages'].append(run(command, stage, 'public-pins', 900, env))
            junit = ET.parse(stage / 'results.xml').getroot()
            cases = junit.findall('.//testcase')
            assert len(cases) == 4 and {case.get('name') for case in cases} == GROUPS
            assert all(not list(case) for case in cases), 'failure/error/skip in public suite'
            log = (stage / 'public-pins.log').read_text(encoding='utf-8')
            assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in log
            records = audit_records(stage / 'records')
            observed[simulator] = records
            result[simulator] = {'groups': 4, 'cases': len(records), 'expected_rejections': 15,
                                 'junit_sha256': digest(stage / 'results.xml'), 'records': records}
            save()
            print(simulator, 'PASS_ASSEMBLED_PUBLIC_PROGRAMS', len(records), 'cases', flush=True)
        if len(observed) == 2:
            assert observed['icarus'] == observed['verilator'], 'simulators disagree on public traces or controls'
            result['status'] = 'PASS_ASSEMBLER_AND_BOTH_PUBLIC_SIMULATORS'
        else:
            result['status'] = 'PASS_ASSEMBLER_AND_ONE_PUBLIC_SIMULATOR'
        assert verify(ROOT) == result['production']
        assert verification_inputs() == result['inputs_sha256'], 'producing inputs changed during verification'
        result['scope'] = 'Software/toolchain qualification on unchanged G2 production RTL with public-pin observations. No new physical, analog, silicon or owner-fluency result.'
        return result
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--simulator', choices=('icarus', 'verilator'), action='append')
    parser.add_argument('--build-only', action='store_true')
    args = parser.parse_args()
    simulators = args.simulator or ['icarus', 'verilator']
    if len(simulators) != len(set(simulators)):
        parser.error('simulators must be unique')
    output = args.out or ROOT / 'build/programs' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    result = execute(output, simulators, args.build_only)
    print(result['status'], output)
