# SPDX-License-Identifier: Apache-2.0
"""Source-matched SRAM implementation of the normal verification stages."""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from current_profile import ROOT, describe, digest

sys.path.insert(0, str(ROOT / 'experiments/i2c'))
sys.path.insert(0, str(ROOT / 'experiments/spi_phase'))
from build_sram_candidate import build
from run_sram_mapping import blackbox, MACRO
from run_current_regression import check_junit, check_controls, physical
from sram_prefetch import parent_sources

read = lambda path: json.loads(path.read_bytes())
TOP = 'tt_um_khangelani_protocol_emulator'


def materialize_candidate(sources, out):
    profile = describe(sources)
    assert profile['profile'] == 'od128-sram'
    manifest = build(out)
    assert manifest['source_sha256'] == profile['source_sha256']
    assert manifest['model_sha256'] == profile['model_sha256']
    # The actual selected source directory supplies every compiled RTL file.
    for name, expected in profile['source_sha256'].items():
        assert digest(sources / name) == expected
        shutil.copyfile(sources / name, out / 'src' / name)
    return manifest


def style_check(sources, directory):
    directory.mkdir()
    profile = describe(sources)
    assert profile['profile'] == 'od128-sram'
    modules = ('m1_engine.v', 'm1_program_store.v')
    stages = []
    for name, files, flags, expected_code in (
        ('other-modules', [n for n in profile['source_sha256'] if n not in modules], [], 0),
        ('unwaived', list(modules), [], 1),
        ('scoped', list(modules), ['--rules=-always-comb'], 0),
    ):
        command = ['verible-verilog-lint', '--rules_config_search', *flags, *(str(sources / n) for n in files)]
        proc = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        (directory / (name + '.log')).write_bytes(proc.stdout)
        assert proc.returncode == expected_code, proc.stdout.decode()
        if name == 'unwaived':
            lines = proc.stdout.decode().splitlines()
            assert len(lines) == 2
            for line, filename, lineno in zip(lines, modules, (232, 78)):
                assert line.startswith(str(sources / filename) + ':' + str(lineno) + ':')
                assert line.endswith('[Style: combinational-logic] [always-comb]')
        stages.append({'name': name, 'command': command, 'returncode': proc.returncode,
                       'log_sha256': digest(directory / (name + '.log'))})
    result = {'status': 'PASS_TWO_SOURCE_PINNED_VERILOG_STYLE_EXCEPTIONS',
              'sources': profile['source_sha256'], 'stages': stages,
              'exception': 'Only always-comb on the exact next-state engine and SRAM combinational read mux; both retain standard Verilog always @*. All other rules/modules pass.'}
    (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


def execute_stage(action, sources, directory, run):
    candidate = directory / 'candidate'
    manifest = materialize_candidate(sources, candidate)
    if action == 'lint':
        run([sys.executable, 'tools/current_sram.py', '--sources', str(candidate / 'src'),
             '--lint-output', str(directory / 'style')], timeout=400)
    elif action.startswith('rtl-'):
        run([sys.executable, 'experiments/i2c/run_sram_regression.py', '--candidate', str(candidate),
             '--simulator', action.removeprefix('rtl-'), '--output', str(directory / 'run')], timeout=1900)
    elif action == 'formal':
        run([sys.executable, 'experiments/i2c/run_sram_current_formal.py', '--sources', str(sources),
             '--output', str(directory / 'current')], label='current-driver', timeout=3600)
        run([sys.executable, 'tools/run_legacy_formal.py', '--output', str(directory / 'legacy')],
            label='legacy-driver', timeout=1800)
    elif action == 'synth':
        header = blackbox((candidate / 'models' / (MACRO + '.v')).read_bytes())
        header_path = directory / (MACRO + '.vh')
        header_path.write_bytes(header)
        script = 'read_verilog -lib -sv ' + str(header_path) + '; read_verilog ' + ' '.join(str(candidate / 'src' / n) for n in manifest['source_sha256'])
        script += f'; hierarchy -check -top {TOP}; synth -top {TOP}; check -assert; stat; write_json {directory / "synth.json"}'
        (directory / 'synth.ys').write_text(script + '\n')
        run(['yosys', '-Q', '-s', str(directory / 'synth.ys')], timeout=300)
    elif action == 'smoke':
        env = dict(os.environ)
        for key in ('GATES', 'G1_PHYSICAL', 'G2_PHYSICAL', 'GENERAL_IO', 'G2_CURRENT', 'COCOTB_TEST_FILTER',
                    'COCOTB_TESTCASE', 'COCOTB_PLUSARGS', 'MAKEFLAGS', 'LEARNING_VCD', 'M0_LEARNING', 'COMPILE_ARGS'):
            env.pop(key, None)
        env.update(G2_SRAM='yes', SRAM_MODEL_DIR=str(candidate / 'models'))
        waveform = ROOT / 'test/tb-gl-harness.fst'
        waveform.unlink(missing_ok=True)
        run(['make', '-C', 'test', 'SIM=icarus', 'SRC_DIR=' + str(candidate / 'src'),
             'SIM_BUILD=' + str(directory / 'sim'),
             'COMPILE_ARGS=-DGL_TEST -DGL_HARNESS_SMOKE -DG2_SRAM -DFUNCTIONAL -DSYNTHESIS',
             'COCOTB_TEST_MODULES=test_gate_harness_smoke', 'COCOTB_RESULTS_FILE=' + str(directory / 'results.xml')],
            timeout=120, env=env)
        shutil.copyfile(waveform, directory / waveform.name)
    else:
        raise ValueError('unsupported SRAM stage: ' + action)


def audit_prediction(directory, sources):
    result = read(directory / 'result.json')
    assert result['status'] == 'PASS_PREFETCH_PREDICTION_INVARIANT_AND_ACTUAL_COUNTEREXAMPLE'
    assert result['sources'] == sources and not result['assumptions']
    original = (directory / 'inputs/m1_engine.v').read_text()
    assert digest(directory / 'inputs/m1_engine.v') == sources['m1_engine.v']
    prop = (directory / 'inputs/property.vh').read_text()
    assert digest(directory / 'inputs/property.vh') == result['property_sha256']
    assert digest(directory / 'inputs/run_prefetch_invariant.py') == result['runner_sha256']
    assert [(t['name'], t['mode'], t['expected']) for t in result['tasks']] == [
        ('prediction', 'prove', 'PASS'), ('moving-pc', 'cover', 'PASS'), ('wrong-low-bit', 'bmc', 'FAIL')]
    from run_prefetch_invariant import inspect_counterexample, PROPERTY
    assert prop == PROPERTY
    assert result['runner_sha256'] == digest(ROOT / 'experiments/i2c/run_prefetch_invariant.py')
    for item in result['tasks']:
        path = directory / item['name']
        assert item['accepted'] and item['execution']['returncode'] == 0 and not item['execution']['timed_out']
        assert (path / 'proof/status').read_text().split()[0] == item['expected']
        expected = original
        if item['mode'] == 'bmc':
            expected = expected.replace('assign prefetch_pc = pc_next;', "assign prefetch_pc = pc_next ^ 8'h01;")
        expected = expected.replace('endmodule', prop + '\nendmodule')
        assert (path / 'engine.v').read_text() == expected
        assert digest(path / 'engine.v') == item['engine_sha256']
        if item['mode'] == 'prove':
            assert 'successful proof by k-induction' in (path / 'run.log').read_text()
        else:
            assert item['witnesses']
        for name, expected_sha in item['witnesses'].items():
            assert digest(path / name) == expected_sha
        if item['mode'] == 'bmc':
            assert inspect_counterexample(path) == item['counterexample']
    return {'invariant': 'pc equals previous prefetch_pc', 'assumptions': 0, 'proved': 1, 'cover': 1, 'checked_fault': 1}


def audit_current_formal(directory, profile):
    sources = profile['source_sha256']
    current = read(directory / 'current/result.json')
    assert current['status'] == 'PASS_CURRENT_SRAM_COMPOSITION_INSTRUCTIONS_AND_SUPPORT_FORMAL'
    assert current['sources'] == sources and all(s['returncode'] == 0 and not s['timed_out'] for s in current['stages'])
    assert [s['name'] for s in current['stages']] == [
        'engine', 'store-controls', 'store-formal', 'prediction', 'instructions',
        'm1_data_store-prove', 'm1_data_store-cover', 'm1_input_sync-prove',
        'm1_input_sync-cover', 'm1_public_readout', 'host-deadline']
    assert [u['name'] for u in current['units']] == [
        'm1_data_store-prove', 'm1_data_store-cover', 'm1_input_sync-prove',
        'm1_input_sync-cover', 'm1_public_readout']
    assert check_candidate(directory / 'current', profile) == current['candidate']
    for stage in current['stages']:
        assert digest(directory / 'current' / (stage['name'] + '.log')) == stage['log_sha256']
    path = ROOT / 'evidence/E0042-sram-prefetch-screen/ci-95120d8/proof_checks.py'
    spec = importlib.util.spec_from_file_location('sram_composition_audit', path)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    import hashlib
    parent = {name: hashlib.sha256(raw).hexdigest() for name, raw in parent_sources().items()}
    composition = audit.check(directory / 'current', current['candidate'], parent)
    assert current['candidate']['source_sha256'] == sources
    prediction = audit_prediction(directory / 'current/prediction', sources)
    instructions = read(directory / 'current/instructions/result.json')
    assert instructions['status'] == 'PASS_SCOPED_INSTRUCTION_PROOFS'
    assert instructions['engine_style'] == 'next-state'
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
    for unit in current['units']:
        path = directory / 'current' / unit['name']
        assert (path / 'status').read_text().split()[0] == 'PASS'
        for name, expected in unit['inputs'].items():
            assert digest(path / 'src' / name) == expected
            if name in sources:
                assert expected == sources[name]
            if name in profile['model_sha256']:
                assert expected == profile['model_sha256'][name]
        for name, expected in unit['witnesses'].items():
            assert digest(path / name) == expected
        log = (directory / 'current' / (unit['name'] + '.log')).read_text()
        assert unit['witnesses'] if unit['name'].endswith('-cover') else 'successful proof by k-induction' in log
    return {'composition': composition, 'prediction': prediction, 'instruction_tasks': 4, 'support_tasks': 5}


def audit_formal(directory, profile):
    current = audit_current_formal(directory, profile)
    legacy = read(directory / 'legacy/result.json')
    assert legacy['status'] == 'PASS_COMPLETE_HISTORICAL_FORMAL_BASELINE'
    assert len(legacy['tasks']) == 10 and all(t['accepted'] for t in legacy['tasks'])
    for task in legacy['tasks']:
        path = directory / 'legacy' / task['name']
        assert (path / 'status').read_text().split()[0] == task['expected']
        for name, expected in task['input_sha256'].items():
            assert digest(path / 'src' / name) == expected
        for name, expected in task['witnesses'].items():
            assert digest(path / name) == expected
    return {'kind': 'CURRENT_SRAM_COMPOSITION_AND_SOURCE_MATCHED_FORMAL', **current, 'historical_tasks': 10,
            'boundary': 'Vendor digital memory model. Earlier complete-chip equivalence timeouts remain incomplete.'}


def check_candidate(directory, profile):
    manifest = read(directory / 'candidate/manifest.json')
    assert manifest['source_sha256'] == profile['source_sha256']
    assert manifest['model_sha256'] == profile['model_sha256']
    for name, expected in manifest['source_sha256'].items():
        assert digest(directory / 'candidate/src' / name) == expected
    for name, expected in manifest['model_sha256'].items():
        assert digest(directory / 'candidate/models' / name) == expected
    return manifest


def semantic_check(action, directory, profile):
    manifest = check_candidate(directory, profile)
    if action.startswith('rtl-'):
        result = read(directory / 'run/result.json')
        assert result['status'] == 'PASS_SRAM_CURRENT_SIMULATOR' and result['candidate'] == manifest
        simulator = action.removeprefix('rtl-')
        assert [s['simulator'] for s in result['stages']] == [simulator]
        stage = directory / 'run' / simulator
        checked = check_junit(stage / 'results.xml')
        checked['records'] = physical.check_public_records(stage / 'records')
        checked['current_bank_control'] = check_controls(stage / 'records/spi/controls.jsonl')
        assert checked == read(stage / 'check.json') == result['stages'][0]['check']
        return {'kind': 'CURRENT_SRAM_RTL_PUBLIC_AND_DIRECT_CORE', **checked}
    if action == 'formal':
        return audit_formal(directory, profile)
    if action == 'lint':
        result = read(directory / 'style/result.json')
        assert result['status'] == 'PASS_TWO_SOURCE_PINNED_VERILOG_STYLE_EXCEPTIONS'
        assert result['sources'] == profile['source_sha256']
        assert [s['returncode'] for s in result['stages']] == [0, 1, 0]
        for stage in result['stages']:
            assert digest(directory / 'style' / (stage['name'] + '.log')) == stage['log_sha256']
        return {'kind': 'SOURCE_PINNED_VERILOG_STYLE', 'unwaived_warnings': 2, 'exception': result['exception']}
    if action == 'synth':
        from run_comparison import cell_counts
        counts = cell_counts(directory / 'synth.json')
        modules = read(directory / 'synth.json')['modules']
        found = []
        def visit(name):
            for cell in modules[name].get('cells', {}).values():
                if cell['type'] == MACRO:
                    found.append(cell)
                elif cell['type'] in modules:
                    visit(cell['type'])
        visit(TOP)
        assert len(found) == 1 and counts['state_bits'] == 353
        assert int(modules[MACRO]['attributes']['blackbox'], 2) == 1
        assert not modules[MACRO].get('cells')
        return {'kind': 'GENERIC_STANDARD_LOGIC_PLUS_REAL_MACRO_BLACKBOX_NOT_PHYSICAL', **counts,
                'macro_count': 1, 'separate_physical_memory_bits': 8192, 'logical_words': 128}
    raise ValueError('unsupported SRAM semantic check: ' + action)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', type=Path, required=True)
    parser.add_argument('--lint-output', type=Path, required=True)
    args = parser.parse_args()
    style_check(args.sources.resolve(), args.lint_output.resolve())
    print('PASS_TWO_SOURCE_PINNED_VERILOG_STYLE_EXCEPTIONS')
