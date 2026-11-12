# SPDX-License-Identifier: Apache-2.0
"""Run the unchanged public physical selection against an identified real netlist."""
import argparse
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

from sram_prefetch import ROOT, digest
from run_current_regression import INPUTS

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from tools import physical_g2
from run_program_sensitivity import execute

read = lambda p: json.loads(p.read_bytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--physical', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--simulator', choices=('icarus', 'verilator'), required=True)
    p.add_argument('--pdk-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    base, candidate, out = args.physical.resolve(), args.candidate.resolve(), args.output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    manifest = read(candidate / 'manifest.json')
    preparation = read(base / 'preparation.json')
    assert manifest == preparation['candidate'] == read(ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json')
    run = base / 'runs/integrated'
    # Require completed routed extraction/STA. Later manufacturing checks can
    # run independently; their observed outcome is not a physical acceptance.
    assert (base / 'run-result.json').exists()
    outcome = read(base / 'run-result.json')
    assert outcome['mode'] == 'full'
    states = sorted(run.glob('*-openroad-stapostpnr/state_out.json'))
    assert len(states) == 1
    state = read(states[0])
    netlist = Path(state['nl'])
    assert netlist.is_relative_to(run) and netlist.is_file()
    text = netlist.read_text()
    assert 'sg13cmos5l_' in text
    assert len(re.findall(r'RM_IHPSG13_1P_256x32_c2_bm_bist\s+\\store\.program_memory\s', text)) == 1
    assert not re.search(r'\b(always|initial)\s*(@|begin)', text)
    (out / 'inputs').mkdir(parents=True)
    (out / 'models').mkdir()
    (out / 'netlist.v').write_bytes(netlist.read_bytes())
    names = set(INPUTS) | {'experiments/i2c/run_sram_netlist.py', 'docs/specs/g2-sram-physical-integration.md',
                          'tools/doctor.py', 'tools/workbench/toolchain.lock.json',
                          'tools/workbench/Dockerfile', 'tools/workbench/requirements.lock'}
    inputs = {}
    for name in sorted(names):
        raw = (ROOT / name).read_bytes()
        target = out / 'inputs' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        inputs[name] = digest(raw)
    for name, expected in manifest['model_sha256'].items():
        raw = (candidate / 'models' / name).read_bytes()
        assert digest(raw) == expected
        (out / 'models' / name).write_bytes(raw)
    for name, expected in manifest['source_sha256'].items():
        assert digest((candidate / 'src' / name).read_bytes()) == expected
        assert digest((base / 'src' / name).read_bytes()) == expected
    pdk = args.pdk_root.resolve()
    libraries = [pdk / 'ihp-sg13cmos5l/libs.ref' / library / 'verilog' / name for library, name in (
        ('sg13cmos5l_io', 'sg13cmos5l_io.v'), ('sg13cmos5l_stdcell', 'sg13cmos5l_udp.v'),
        ('sg13cmos5l_stdcell', 'sg13cmos5l_stdcell.v'))]
    result = {'status': 'RUNNING', 'simulator': args.simulator, 'candidate': manifest,
              'netlist_sha256': digest(netlist.read_bytes()), 'physical_run_outcome': outcome,
              'physical_state_sha256': digest(states[0].read_bytes()),
              'inputs': inputs, 'library_sha256': {str(path): digest(path.read_bytes()) for path in libraries},
              'evidence_kind': 'FUNCTIONAL_ZERO_DELAY_NETLIST', 'physical_qualification': 'SEPARATE_GATE'}
    save = lambda: (out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    save()
    env = dict(os.environ, G2_PHYSICAL='yes', G2_SRAM='yes', SRAM_MODEL_DIR=str(out / 'models'),
               I2C_GENERAL_VARIANT='od128', I2C_GENERAL_RECORD_DIR=str(out / 'records/i2c'), I2C_GENERAL_SMOKE='0',
               TIMED_GPIO_VARIANT='compact10', TIMED_GPIO_RECORD_DIR=str(out / 'records/spi'), TIMED_GPIO_SMOKE='0',
               COCOTB_RANDOM_SEED='20261112', PDK_ROOT=str(pdk))
    for key in ('G2_CURRENT', 'G1_PHYSICAL', 'GENERAL_IO', 'MAKEFLAGS', 'COCOTB_TESTCASE', 'COCOTB_TEST_FILTER'):
        env.pop(key, None)
    command = ['make', '-C', 'test', 'GATES=yes', 'SIM=' + args.simulator,
               'GATE_LEVEL_NETLIST=' + str(out / 'netlist.v'), 'SRC_DIR=' + str(candidate / 'src'),
               'SIM_BUILD=' + str(out / 'sim'), 'COCOTB_RESULTS_FILE=' + str(out / 'results.xml'),
               'FST=', 'COCOTB_PLUSARGS=+NO_DUMP']
    try:
        result['doctor'] = execute([sys.executable, str(ROOT / 'tools/doctor.py')], out / 'doctor.log', 60)
        assert result['doctor']['returncode'] == 0 and not result['doctor']['timed_out']
        assert 'RESULT: PASS' in (out / 'doctor.log').read_text()
        result['execution'] = execute(command, out / 'run.log', 10800, env=env)
        assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
        physical_g2.check_tests(SimpleNamespace(junit=out / 'results.xml', records=out / 'records',
                                                output=out / 'check.json', require_netlist=False))
        checks = read(out / 'check.json')
        checks.update(variant='od128-sram', netlist_sha256=result['netlist_sha256'],
                      evidence_kind='FUNCTIONAL_ZERO_DELAY_NETLIST')
        result['checks'] = checks
        log = (out / 'run.log').read_text()
        assert ('Running on Icarus Verilog' if args.simulator == 'icarus' else 'Running on Verilator') in log
        assert str(out / 'netlist.v') in log and all(str(path) in log for path in libraries)
        assert all(flag in log for flag in ('-DGL_TEST', '-DG2_SRAM', '-DFUNCTIONAL', '-DSYNTHESIS'))
        assert not any(str(candidate / 'src' / name) in log for name in manifest['source_sha256'])
        assert digest(netlist.read_bytes()) == digest((out / 'netlist.v').read_bytes()) == result['netlist_sha256']
        assert {name: digest((ROOT / name).read_bytes()) for name in inputs} == inputs
        result['status'] = 'PASS_SRAM_ACTUAL_NETLIST_PUBLIC_SELECTION'
    except Exception as error:
        result.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        save()
    print(result['status'])


if __name__ == '__main__':
    main()
