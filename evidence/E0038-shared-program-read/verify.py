# SPDX-License-Identifier: Apache-2.0
"""Replay D39 source, full public records, actual proof models and fault witnesses."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/i2c'))
from tools import physical_g2 as physical
from shared_read import generate, PARENT
from run_shared_read_controls import MUTATIONS, expected_record
from run_shared_read_proof import state_matches, check_temporal, check_reset


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit_proof(path, sources):
    result = read(path / 'result.json')
    assert result['status'] == 'PASS_RESET_REACHABLE_COMPLETE_CHIP_EQUIVALENCE'
    expected = {'gold': read(PARENT / 'sources/source-manifest.json')['od128']['source_sha256'], 'gate': sources}
    assert result['sources'] == expected
    assert set(result['stages']) == {'gold', 'gate', 'temporal', 'reset'}
    for name, stage in result['stages'].items():
        assert stage['returncode'] == 0 and not stage['timed_out']
        assert stage['command'][:3] == ['yosys', '-Q', '-s']
        script = Path(stage['command'][3])
        assert script.name == name + '.ys'
        assert stage['wall_limit'] == (300 if name == 'temporal' else 90 if name == 'reset' else 60)
        assert 'Yosys 0.67+111' in (path / (name + '.log')).read_text()
    for name, expected_hash in result['model_sha256'].items():
        assert sha((path / name).read_bytes()) == expected_hash
    assert set(result['model_sha256']) == {'gold.il', 'gate.il', 'gold.json', 'gate.json',
                                         'before.json', 'after.json', 'reset.json', 'blacklist.txt'}
    models = {label: read(path / (label + '.json'))['modules'][label] for label in ('gold', 'gate')}
    states, excluded = state_matches(models)
    assert states == result['common_state_names'] and excluded == result['excluded_combinational_names']
    assert (path / 'blacklist.txt').read_text().splitlines() == excluded
    count = check_temporal(read(path / 'before.json')['modules']['equivalence'],
                           read(path / 'after.json')['modules']['equivalence'], states)
    reset = check_reset(read(path / 'reset.json')['modules']['equivalence'], states, count)
    assert result['reset_base'] == reset
    assert result['actual_state_bits_per_chip'] == 4278 and result['public_output_bits'] == 24
    assert result['proven_bit_comparisons_including_aliases'] == count == 4572
    assert result['temporal_maximum_step'] == 1
    assert 'Equivalence successfully proven!' in (path / 'temporal.log').read_text()
    assert 'SAT proof finished - no model found: SUCCESS!' in (path / 'reset.log').read_text()
    # Bind the successful stages to the complete sources and exact proof commands.
    base = Path(result['stages']['gold']['command'][3]).parent.as_posix()
    gold_script = (path / 'gold.ys').read_text().strip()
    gate_script = (path / 'gate.ys').read_text().strip()
    for label, script in (('gold', gold_script), ('gate', gate_script)):
        prefix = script.split(';', 1)[0]
        assert prefix.startswith('read_verilog ')
        names = prefix.removeprefix('read_verilog ').split()
        assert [Path(n).name for n in names] == list(expected[label])
        if label == 'gold':
            assert all('/evidence/E0037-explicit-store-lanes/sources/od128/' in n for n in names)
        else:
            assert len({str(Path(n).parent) for n in names}) == 1
            assert all('/variants/od128/src/' in n for n in names)
        after = f'; hierarchy -check -top tt_um_khangelani_protocol_emulator; proc; flatten; opt; check -assert; rename tt_um_khangelani_protocol_emulator {label}; '
        after += f'write_rtlil {base}/{label}.il; write_json {base}/{label}.json'
        assert script == prefix + after
    inputs = f'read_rtlil {base}/gold.il {base}/gate.il; '
    temporal = inputs + f'equiv_make -blacklist {base}/blacklist.txt gold gate equivalence; hierarchy -top equivalence; '
    temporal += f'write_json {base}/before.json; equiv_simple; equiv_induct -seq 1; equiv_status -assert; write_json {base}/after.json'
    reset_script = inputs + f'equiv_make -make_assert -blacklist {base}/blacklist.txt gold gate equivalence; '
    reset_script += f'hierarchy -top equivalence; dffunmap; opt_clean; write_json {base}/reset.json; '
    reset_script += 'sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports'
    assert (path / 'temporal.ys').read_text().strip() == temporal
    assert (path / 'reset.ys').read_text().strip() == reset_script
    return {'actual_state_bits_per_chip': 4278, 'public_output_bits': 24,
            'proven_bit_comparisons_including_aliases': count, 'reset_base': reset}


def audit_controls(path, sources):
    result = read(path / 'result.json')
    assert result['status'] == 'PASS_PUBLIC_SHARED_READ_MUTATION_CONTROLS' and result['sources'] == sources
    original, _ = generate()
    identities = [(s['control'], s['simulator']) for s in result['stages']]
    assert identities == [(c, sim) for c in ('baseline', *MUTATIONS) for sim in ('icarus', 'verilator')]
    for stage in result['stages']:
        control, simulator = stage['control'], stage['simulator']
        expected = dict(original)
        if control != 'baseline':
            before, after = MUTATIONS[control]
            assert expected['m1_program_store.v'].decode().count(before) == 1
            expected['m1_program_store.v'] = expected['m1_program_store.v'].decode().replace(before, after).encode()
        assert {n: sha(raw) for n, raw in expected.items()} == stage['source_sha256']
        assert all((path / control / 'src' / n).read_bytes() == raw for n, raw in expected.items())
        observed = path / control / simulator
        raw = (observed / 'observations.json').read_bytes()
        assert sha(raw) == stage['observations_sha256']
        actual = json.loads(raw)
        assert actual == expected_record(control)
        assert (actual == expected_record('baseline')) == stage['baseline_accepted'] == (control == 'baseline')
        assert stage['expected_mutant_rejection'] == (control != 'baseline')
        cases = ET.parse(observed / 'results.xml').getroot().findall('.//testcase')
        assert len(cases) == 1 and not list(cases[0])
        assert cases[0].get('name') == 'public_shared_read_witness' and cases[0].get('classname') == 'test_shared_read_controls'
        assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in (observed / 'run.log').read_text()
    return {'public_simulators': ['icarus', 'verilator'], 'baseline_passes': 2, 'checked_mutant_counterexamples': 6}


def audit_selection(path, sources, output):
    result = read(path / 'result.json')
    assert result['status'] == 'PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS' and result['sources'] == sources
    assert [s['simulator'] for s in result['stages']] == ['icarus', 'verilator']
    checks = {}
    for stage in result['stages']:
        simulator = stage['simulator']
        subdir = path / simulator
        assert stage['returncode'] == 0
        assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in (subdir / 'run.log').read_text()
        checked = output / (simulator + '-public.json')
        physical.check_tests(SimpleNamespace(junit=subdir / 'results.xml', records=subdir / 'records',
                                            output=checked, require_netlist=False))
        assert read(checked) == stage['check'] == read(subdir / 'check.json')
        checks[simulator] = {'public_test_groups': 18, 'records': stage['check']['records'],
                            'junit_sha256': sha((subdir / 'results.xml').read_bytes())}
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((ROOT / 'build').resolve()) and not out.exists(), 'new build output required'
    out.mkdir(parents=True)
    index = read(HERE / 'archives.json')
    assert set(index) == {'selection', 'proof', 'controls', 'style'}
    sources = read(HERE / 'sources/source-manifest.json')['od128']['source_sha256']
    parent = read(PARENT / 'qualification.json')
    assert parent['status'] == 'PASS_LANES_CANDIDATE_RTL_FORMAL'
    assert parent['source_sha256'] == read(PARENT / 'sources/source-manifest.json')['od128']['source_sha256']
    assert physical.verify_sources(HERE / 'sources/od128', 'od128-shared') == sources
    for gate, entry in index.items():
        packed = HERE / (gate + '.tar.gz')
        assert sha(packed.read_bytes()) == entry['archive_sha256']
        target = out / gate
        with tarfile.open(packed) as archive:
            members = archive.getmembers()
            assert len(members) == len(entry['files']) and {m.name for m in members} == set(entry['files'])
            for member in members:
                path = (target / member.name).resolve()
                assert member.isfile() and path.is_relative_to(target.resolve())
                raw = archive.extractfile(member).read()
                assert sha(raw) == entry['files'][member.name]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    assert physical.verify_sources(out / 'selection/variants/od128/src', 'od128-shared') == sources
    proof = audit_proof(out / 'proof', sources)
    controls = audit_controls(out / 'controls', sources)
    subprocess.run([sys.executable, str(ROOT / 'experiments/i2c/falsify_shared_read_audit.py'),
                    '--proof', str(out / 'proof'), '--controls', str(out / 'controls'),
                    '--output', str(out / 'audit-controls')], cwd=ROOT, check=True)
    audit_controls_result = read(out / 'audit-controls/result.json')
    assert audit_controls_result == read(HERE / 'audit-controls/result.json')
    assert audit_controls_result['status'] == 'PASS_SHARED_AUDIT_NEGATIVE_CONTROLS'
    assert len(audit_controls_result['controls']) == 10 and all(c['rejected'] for c in audit_controls_result['controls'])
    selection = audit_selection(out / 'selection/selection', sources, out)
    style = read(out / 'style/result.json')
    assert style['status'] == 'PASS_SCOPED_STYLE_REVIEW' and style['sources'] == sources
    assert [s['name'] for s in style['stages']] == ['other-modules', 'store-unwaived', 'store-scoped']
    for stage in style['stages']:
        raw = (out / 'style' / (stage['name'] + '.log')).read_bytes()
        assert sha(raw) == stage['log_sha256']
        if stage['name'] == 'store-unwaived':
            assert stage['returncode'] == 1 and len(raw.splitlines()) == 129
            assert sum(line.endswith(b'[case-missing-default]') for line in raw.splitlines()) == 128
            assert sum(line.endswith(b'[always-comb]') for line in raw.splitlines()) == 1
        else:
            assert stage['returncode'] == 0
    report = {'status': 'PASS_SHARED_CANDIDATE_RTL_FORMAL', 'implementation': 'od128-shared', 'source_sha256': sources,
              'program_words': 128, 'program_bits': 4096, 'complete_chip_proof': proof, 'mutation_controls': controls,
              'public_simulators': selection, 'archives': {k: v['archive_sha256'] for k, v in index.items()},
              'style_review': {'status': style['status'], 'unwaived_warnings': 129, 'exception': style['exception']},
              'parent_qualification_sha256': sha((PARENT / 'qualification.json').read_bytes()),
              'rejected_audit_corruptions': 10,
              'inheritance': 'Complete-chip reset-reachable equivalence to D38. All 128 words and control bits remain real; inactive internal read-port values intentionally differ.',
              'physical': 'NOT_YET_QUALIFIED', 'production': 'UNCHANGED'}
    if (HERE / 'qualification.json').exists():
        assert report == read(HERE / 'qualification.json')
    (out / 'qualification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(report['status'])


if __name__ == '__main__':
    main()
