# SPDX-License-Identifier: Apache-2.0
"""Current 128-word profile: all public groups and compatible direct-core checks."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools import physical_g2 as physical

REQUIRED = ({(module, name) for name, module in physical.PUBLIC_TEST_MODULES.items()}
            | physical.common.EXCLUDED_TESTS | {
                ('test_spi_mode0_public', 'spi_mode0_public_conditional_and_counterexample'),
                ('test_spi_mode0_public', 'spi_mode0_abort_reload_and_capacity_boundary')})
INPUTS = ['test/Makefile', 'test/tb.v', 'test/test.py', 'test/test_uart_rx_public.py',
          'test/test_spi_mode0_public.py', 'test/test_spi_timed_gpio.py', 'test/test_i2c_general_public.py',
          'test/test_general_boundaries.py', 'test/test_i2c_abort_public.py', 'tools/physical_g2.py',
          'tools/physical_candidate.py', 'tools/i2c_oracle.py', 'tools/spi_four_mode_oracle.py',
          'tools/spi_mode0_oracle.py', 'tools/uart_rx_oracle.py', 'tools/m1_contract_model.py',
          'experiments/i2c/run_current_regression.py', 'experiments/i2c/general_programs.py',
          'experiments/i2c/public_bus.py', 'experiments/i2c/target.py',
          'experiments/spi_phase/timed_gpio_programs.py']


def check_junit(path):
    root = ET.parse(path).getroot()
    cases = root.findall('.//testcase')
    identities = [(c.get('classname'), c.get('name')) for c in cases]
    assert len(REQUIRED) == 30 and len(identities) == len(set(identities)) == 30
    assert set(identities) == REQUIRED, set(identities) ^ REQUIRED
    assert not any(root.findall('.//' + tag) for tag in ('failure', 'error', 'skipped'))
    for suite in root.iter('testsuite'):
        assert not any(int(suite.get(k, '0')) for k in ('failures', 'errors', 'skipped'))
    return {'test_groups': 30, 'required': sorted('.'.join(i) for i in REQUIRED), 'junit_sha256': physical.digest(path)}


def check_controls(path):
    rows = physical.records(path)
    words = [0x10203040 + i * 0x01010101 for i in range(10)]
    expected = [[i, lane, (word >> (8 * lane)) & 255]
                for i, word in [*enumerate(words), (127, 0x91827364)] for lane in range(4)]
    assert rows == [{'name': 'current-banked-nonalias', 'accepted': True, 'observations': expected, 'invalid_bank': 16}]
    return {'status': 'PASS', 'observations': len(expected), 'sha256': physical.digest(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--implementation', choices=('od128-shared', 'od128-lanes'), default='od128-shared')
    parser.add_argument('--simulator', choices=('icarus', 'verilator'), action='append')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or not out.is_relative_to((ROOT / 'build').resolve()):
        raise ValueError('new isolated output required')
    out.mkdir(parents=True)
    src = args.sources.resolve()
    sources = physical.verify_sources(src, args.implementation)
    inputs = {name: physical.digest(ROOT / name) for name in INPUTS}
    result = {'status': 'RUNNING', 'implementation': args.implementation, 'sources': sources,
              'source_directory': str(src), 'verification_inputs': inputs, 'stages': [],
              'scope': 'CURRENT_RTL_PUBLIC_AND_DIRECT_CORE_30_GROUPS', 'physical': 'NOT_EVALUATED'}
    simulators = args.simulator or ['icarus', 'verilator']
    assert len(simulators) == len(set(simulators))

    def save():
        physical.write_json(out / 'result.json', result)

    save()
    try:
        for simulator in simulators:
            stage = out / simulator
            stage.mkdir()
            env = dict(os.environ)
            for key in ('GATES', 'G1_PHYSICAL', 'G2_PHYSICAL', 'GENERAL_IO', 'MAKEFLAGS', 'COCOTB_TESTCASE',
                        'COCOTB_TEST_FILTER', 'COCOTB_TEST_MODULES', 'COMPILE_ARGS', 'LEARNING_VCD', 'M0_LEARNING'):
                env.pop(key, None)
            env.update(G2_CURRENT='yes', I2C_GENERAL_VARIANT='od128', I2C_GENERAL_SMOKE='0',
                       I2C_GENERAL_RECORD_DIR=str(stage / 'records/i2c'), TIMED_GPIO_VARIANT='compact10',
                       TIMED_GPIO_SMOKE='0', TIMED_GPIO_RECORD_DIR=str(stage / 'records/spi'), COCOTB_RANDOM_SEED='20261112')
            command = ['make', '-C', 'test', 'SIM=' + simulator, 'SRC_DIR=' + str(src),
                       'SIM_BUILD=' + str(stage / 'sim'), 'COCOTB_RESULTS_FILE=' + str(stage / 'results.xml'),
                       'FST=', 'COCOTB_PLUSARGS=+NO_DUMP']
            start = time.monotonic()
            with (stage / 'run.log').open('w') as log:
                proc = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            assert proc.returncode == 0, 'current combined regression failed'
            text = (stage / 'run.log').read_text()
            assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in text
            assert 'expects 8 bit(s), given 5' not in text
            check = check_junit(stage / 'results.xml')
            check['records'] = physical.check_public_records(stage / 'records')
            check['current_bank_control'] = check_controls(stage / 'records/spi/controls.jsonl')
            physical.write_json(stage / 'check.json', check)
            result['stages'].append({'simulator': simulator, 'returncode': proc.returncode, 'command': command,
                                     'seconds': round(time.monotonic() - start, 3), 'check': check})
            save()
        assert physical.verify_sources(src, args.implementation) == sources
        assert {name: physical.digest(ROOT / name) for name in INPUTS} == inputs, 'verification inputs changed during execution'
        result['status'] = 'PASS_CURRENT_RTL_BOTH_SIMULATORS' if set(simulators) == {'icarus', 'verilator'} else 'PASS_CURRENT_RTL_SIMULATOR'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'], flush=True)


if __name__ == '__main__':
    main()
