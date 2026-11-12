# SPDX-License-Identifier: Apache-2.0
"""Run and package the current profile, binding reusable results to exact inputs."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from current_profile import ROOT, describe, digest, verification_inputs

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/i2c'))
from run_current_regression import check_junit, check_controls
from tools import physical_g2 as physical

STAGES = ('doctor', 'check', 'lint', 'rtl-icarus', 'rtl-verilator', 'formal', 'synth', 'smoke')
TOP = 'tt_um_khangelani_protocol_emulator'


def runtime_identity():
    env = dict(os.environ, PROTOCOL_EMULATOR_LOCKED_WORKBENCH='1')
    result = subprocess.run([sys.executable, str(ROOT / 'tools/doctor.py')], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, 'current verification requires the pinned tools: ' + result.stdout + result.stderr
    import hashlib
    return hashlib.sha256(result.stdout.encode()).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + '\n').encode())


def retained_files(directory):
    suffixes = {'.json', '.jsonl', '.xml', '.log', '.v', '.sv', '.vh', '.sby', '.ys', '.il', '.vcd', '.fst', '.txt'}
    return {p.relative_to(directory).as_posix(): digest(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and 'sim' not in p.relative_to(directory).parts and '__pycache__' not in p.parts
            and (p.suffix in suffixes or p.name in ('status', 'PASS', 'FAIL'))}


def semantic_check(action, directory, profile):
    sources = profile['source_sha256']
    if profile['profile'] == 'od128-sram' and action in ('rtl-icarus', 'rtl-verilator', 'formal', 'lint', 'synth'):
        from current_sram import semantic_check as check_sram
        return check_sram(action, directory, profile)
    if action.startswith('rtl-'):
        result = read(directory / 'run/result.json')
        assert result['status'] == 'PASS_CURRENT_RTL_SIMULATOR' and result['sources'] == sources
        simulator = action.removeprefix('rtl-')
        assert [s['simulator'] for s in result['stages']] == [simulator]
        stage = directory / 'run' / simulator
        checked = check_junit(stage / 'results.xml')
        checked['records'] = physical.check_public_records(stage / 'records')
        checked['current_bank_control'] = check_controls(stage / 'records/spi/controls.jsonl')
        assert checked == read(stage / 'check.json') == result['stages'][0]['check']
        return {'kind': 'CURRENT_RTL_PUBLIC_AND_DIRECT_CORE', **checked}
    if action == 'formal':
        result, legacy = read(directory / 'current/result.json'), read(directory / 'legacy/result.json')
        assert result['status'] == 'PASS_CURRENT_CHIP_INSTRUCTION_AND_SUPPORT_FORMAL' and result['sources'] == sources
        assert len(result['stages']) == 8 and all(s['returncode'] == 0 for s in result['stages'])
        assert legacy['status'] == 'PASS_COMPLETE_HISTORICAL_FORMAL_BASELINE'
        assert len(legacy['tasks']) == 10 and all(t['accepted'] for t in legacy['tasks'])
        spec = importlib.util.spec_from_file_location('current_chip_audit', ROOT / 'evidence/E0038-shared-program-read/verify.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        chip = audit.audit_proof(directory / 'current/chip', sources)
        instructions = read(directory / 'current/instructions/result.json')
        assert instructions['status'] == 'PASS_SCOPED_INSTRUCTION_PROOFS'
        assert instructions['sources'] == {'od128': sources['m1_engine.v']}
        assert len(instructions['tasks']) == 4 and all(t['accepted'] for t in instructions['tasks'])
        from run_general_formal import inspect_control
        for task in instructions['tasks']:
            path = directory / 'current/instructions' / ('od128-' + task['name'])
            assert (path / 'proof/status').read_text().split()[0] == task['expected']
            assert digest(path / 'engine.v') == task['input_sha256']
            for name, expected in task['witnesses'].items():
                assert digest(path / name) == expected
            if task['mode'] == 'bmc':
                assert inspect_control(task['name'], path) == task['control']
        assert len(result['units']) == 5
        for unit in result['units']:
            path = directory / 'current' / unit['name']
            assert (path / 'status').read_text().split()[0] == 'PASS'
            for name, expected in unit['inputs'].items():
                assert digest(path / 'src' / name) == expected
                if name in sources:
                    assert expected == sources[name]
            for name, expected in unit['witnesses'].items():
                assert digest(path / name) == expected
            log = (directory / 'current' / (unit['name'] + '.log')).read_text()
            assert unit['witnesses'] if unit['name'].endswith('-cover') else 'successful proof by k-induction' in log
        for task in legacy['tasks']:
            path = directory / 'legacy' / task['name']
            assert (path / 'status').read_text().split()[0] == task['expected']
            for name, expected in task['input_sha256'].items():
                assert digest(path / 'src' / name) == expected
            for name, expected in task['witnesses'].items():
                assert digest(path / name) == expected
        return {'kind': 'CURRENT_FORMAL_WITH_SEPARATE_HISTORICAL_BASELINE', 'chip': chip,
                'current_instruction_tasks': 4, 'current_support_tasks': 5, 'historical_tasks': 10}
    if action == 'lint':
        result = read(directory / 'style/result.json')
        assert result['status'] == 'PASS_SCOPED_STYLE_REVIEW' and result['sources'] == sources
        assert [s['returncode'] for s in result['stages']] == [0, 1, 0]
        for stage in result['stages']:
            assert digest(directory / 'style' / (stage['name'] + '.log')) == stage['log_sha256']
        return {'kind': 'SCOPED_STYLE', 'unwaived_warnings': 129, 'exception': result['exception']}
    if action == 'synth':
        sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
        from run_comparison import cell_counts
        counts = cell_counts(directory / 'synth.json')
        assert counts['state_bits'] == 4278 and counts['primitive_cells'] == 15211
        assert not any('latch' in name.lower() for name in counts['cell_types'])
        return {'kind': 'GENERIC_SYNTHESIS_NOT_PHYSICAL', **counts}
    if action == 'smoke':
        if profile['profile'] == 'od128-sram':
            from current_sram import check_candidate
            check_candidate(directory, profile)
        root = ET.parse(directory / 'results.xml').getroot()
        for suite in root.iter('testsuite'):
            assert all(int(suite.get(key, '0')) == 0 for key in ('failures', 'errors', 'skipped'))
        cases = root.findall('.//testcase')
        assert len(cases) == 1 and not list(cases[0])
        assert cases[0].get('classname') == 'test_gate_harness_smoke'
        assert cases[0].get('name') == 'public_handles_reset_without_direct_engine'
        assert (directory / 'tb-gl-harness.fst').stat().st_size > 0
        return {'kind': 'RTL_HARNESS_SMOKE_NOT_NETLIST', 'tests': 1,
                'junit_sha256': digest(directory / 'results.xml'), 'waveform_sha256': digest(directory / 'tb-gl-harness.fst')}
    return {'kind': 'PINNED_TOOL_IDENTITY' if action == 'doctor' else 'REPOSITORY_CHECKS'}


def load_receipt(artifacts, action, profile, inputs, runtime=None):
    assert action != 'check', 'repository checks must run fresh during collection'
    receipt = read(artifacts / 'receipts' / (action + '.json'))
    assert receipt['schema'] == 'protocol-emulator-current-stage-v1' and receipt['status'] == 'PASS'
    assert receipt['action'] == action and receipt['profile'] == profile
    assert receipt['verification_inputs'] == inputs, 'verification inputs changed since the stage ran'
    if runtime is not None:
        assert receipt['runtime_identity'] == runtime, 'verification runtime changed'
    assert receipt['commands'] and all(c['returncode'] == 0 for c in receipt['commands'])
    directory = (ROOT / receipt['directory']).resolve()
    assert directory.is_relative_to(artifacts.resolve()), 'stage directory escapes its artifact root'
    assert receipt['artifact_sha256'] == retained_files(directory), 'missing, changed or extra stage artifacts'
    assert receipt['summary'] == semantic_check(action, directory, profile)
    return receipt


def execute_stage(action, sources, artifacts, runtime):
    profile, inputs = describe(sources), verification_inputs()
    assert profile['profile'] in ('od128-shared', 'od128-sram'), 'current commands require a declared current candidate'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    directory = artifacts / 'runs' / (stamp + '-' + action)
    directory.mkdir(parents=True)
    receipt_path = artifacts / 'receipts' / (action + '.json')
    receipt = {'schema': 'protocol-emulator-current-stage-v1', 'action': action, 'status': 'RUNNING',
               'created_utc': stamp, 'profile': profile, 'source_directory': str(sources), 'runtime_identity': runtime,
               'directory': directory.relative_to(ROOT).as_posix(), 'verification_inputs': inputs,
               'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'commands': []}
    write(receipt_path, receipt)

    def run(command, label='run', timeout=1800, env=None):
        with (directory / (label + '.log')).open('w') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env)
        receipt['commands'].append({'command': command, 'returncode': process.returncode, 'timeout_seconds': timeout})
        assert process.returncode == 0, action + ' failed; see ' + str(directory / (label + '.log'))

    try:
        if action == 'doctor':
            run([sys.executable, 'tools/doctor.py'], timeout=120)
        elif action == 'check':
            run(['make', 'check-base'], timeout=300)
        elif profile['profile'] == 'od128-sram':
            from current_sram import execute_stage as execute_sram
            execute_sram(action, sources, directory, run)
        elif action == 'lint':
            target = directory / 'variants/od128/src'
            target.mkdir(parents=True)
            for name in profile['source_sha256']:
                shutil.copyfile(sources / name, target / name)
            run([sys.executable, 'experiments/i2c/lint_store_lanes.py', '--variants', str(directory / 'variants'),
                 '--source-revision', 'shared-read', '--output', str(directory / 'style')], timeout=120)
        elif action.startswith('rtl-'):
            run([sys.executable, 'experiments/i2c/run_current_regression.py', '--sources', str(sources),
                 '--simulator', action.removeprefix('rtl-'), '--output', str(directory / 'run')], timeout=1900)
        elif action == 'formal':
            run([sys.executable, 'experiments/i2c/run_current_formal.py', '--sources', str(sources),
                 '--output', str(directory / 'current')], label='current-driver', timeout=1200)
            run([sys.executable, 'tools/run_legacy_formal.py', '--output', str(directory / 'legacy')], label='legacy-driver', timeout=1800)
        elif action == 'synth':
            script = 'read_verilog ' + ' '.join(str(sources / n) for n in profile['source_sha256'])
            script += f'; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {directory / "synth.json"}'
            (directory / 'synth.ys').write_text(script + '\n')
            run(['yosys', '-Q', '-s', str(directory / 'synth.ys')], timeout=300)
        else:
            import os
            env = dict(os.environ)
            for key in ('GATES', 'G1_PHYSICAL', 'G2_PHYSICAL', 'GENERAL_IO', 'G2_CURRENT', 'COCOTB_TEST_FILTER',
                        'COCOTB_TESTCASE', 'COCOTB_PLUSARGS', 'MAKEFLAGS', 'LEARNING_VCD', 'M0_LEARNING'):
                env.pop(key, None)
            waveform = ROOT / 'test/tb-gl-harness.fst'
            waveform.unlink(missing_ok=True)
            run(['make', '-C', 'test', 'SIM=icarus', 'SRC_DIR=' + str(sources), 'SIM_BUILD=' + str(directory / 'sim'),
                 'COMPILE_ARGS=-DGL_TEST -DGL_HARNESS_SMOKE', 'COCOTB_TEST_MODULES=test_gate_harness_smoke',
                 'COCOTB_RESULTS_FILE=' + str(directory / 'results.xml')], timeout=120, env=env)
            shutil.copyfile(waveform, directory / waveform.name)
        assert describe(sources) == profile and verification_inputs() == inputs, 'inputs changed during execution'
        receipt['summary'] = semantic_check(action, directory, profile)
        receipt['artifact_sha256'] = retained_files(directory)
        receipt['status'] = 'PASS'
    except Exception as error:
        receipt.update(status='FAILED_OR_INCOMPLETE', error=str(error))
        raise
    finally:
        write(receipt_path, receipt)
    print('PASS:', action, receipt['directory'], flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=(*STAGES, 'provenance', 'evidence'))
    parser.add_argument('--sources', type=Path, default=ROOT / 'src')
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'build/current')
    args = parser.parse_args()
    artifacts, sources = args.artifacts.resolve(), args.sources.resolve()
    assert artifacts.is_relative_to((ROOT / 'build').resolve()), 'artifact root must be inside build'
    runtime = runtime_identity()
    if args.action in STAGES:
        execute_stage(args.action, sources, artifacts, runtime)
        return
    profile, inputs = describe(sources), verification_inputs()
    assert profile['profile'] in ('od128-shared', 'od128-sram')
    required = STAGES if args.action == 'evidence' else ('rtl-icarus', 'smoke')
    receipts = {}
    for action in required:
        if action == 'check':
            # Learning/history metadata has dependencies beyond the RTL input set.
            receipts[action] = execute_stage(action, sources, artifacts, runtime)
            continue
        try:
            receipts[action] = load_receipt(artifacts, action, profile, inputs, runtime)
        except (AssertionError, OSError, ValueError):
            if args.action != 'evidence':
                raise
            old = artifacts / 'receipts' / (action + '.json')
            if old.exists() and read(old).get('status') == 'RUNNING':
                raise ValueError('An unfinished stage must be inspected before retry: ' + str(old))
            execute_stage(action, sources, artifacts, runtime)
            receipts[action] = load_receipt(artifacts, action, profile, inputs, runtime)
    result = {'schema': 'protocol-emulator-current-evidence-v1', 'status': 'PASS', 'profile': profile,
              'verification_inputs': inputs, 'stages': receipts,
              'scope': 'RTL public traces/direct-core checks, source-matched formal, generic cost and a separate RTL harness smoke waveform. No physical qualification is inferred.',
              'artifact_rule': 'Full RTL stores public trace witnesses and their checksums; only the separate harness smoke test emits an FST. Historical waveform provenance remains on the legacy profile.'}
    write(artifacts / (args.action + '.json'), result)
    print('PASS:', args.action, str(artifacts / (args.action + '.json')), flush=True)


if __name__ == '__main__':
    main()
