# SPDX-License-Identifier: Apache-2.0
"""Verify archived bytes, actual proof comparisons, counts and alias witnesses."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha((HERE / name).read_bytes()) == expected, name
    index = read(HERE / 'archive.json')
    packed = HERE / 'screen.tar.gz'
    assert sha(packed.read_bytes()) == index['sha256']
    with tarfile.open(packed) as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            path = (out / member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    proof = out / 'screen'
    result = read(proof / 'result.json')
    assert result['status'] == 'PASS_BOUNDED_BANKED_READ_PROOF_AND_GENERIC_SCREEN'
    assert result['runner_sha256'] == sha((out / 'inputs/run_banked_read_screen.py').read_bytes())
    assert result['spec_sha256'] == sha((out / 'inputs/g2-banked-read-screen.md').read_bytes())
    limits = {'gold-synth': 300, 'gate-synth': 300, 'gold-model': 60, 'gate-model': 60, 'temporal': 240, 'reset': 90}
    assert set(result['stages']) == set(limits)
    for name, limit in limits.items():
        stage = result['stages'][name]
        assert stage['returncode'] == 0 and stage['timed_out'] is False and stage['wall_limit'] == limit
        assert stage['command'] == ['yosys', '-Q', '-s', '/workspace/build/g2-banked-read-01/' + name + '.ys']
    for label, cells in (('gold', 15211), ('gate', 15593)):
        for name, digest in result['sources'][label].items():
            assert sha((proof / label / 'src' / name).read_bytes()) == digest
        modules = read(proof / (label + '-synth.json'))['modules']
        counts = Counter()
        def visit(name):
            for cell in modules[name].get('cells', {}).values():
                if cell['type'] in modules:
                    visit(cell['type'])
                else:
                    counts[cell['type']] += 1
        visit('tt_um_khangelani_protocol_emulator')
        assert dict(counts) == result['counts'][label]['cell_types']
        assert sum(counts.values()) == cells
        assert sum(n for kind, n in counts.items() if 'DFF' in kind.upper()) == 4278
        assert not any('LATCH' in kind.upper() for kind in counts)
    # Run only the three frozen semantic auditors and their literal port contract.
    # This avoids importing changed repository runners or executing a new solver.
    tree = ast.parse((out / 'inputs/run_banked_read_screen.py').read_bytes())
    definitions = [node for node in tree.body if
                   isinstance(node, ast.FunctionDef) and node.name in ('state_coverage', 'check_comparisons', 'check_reset') or
                   isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'STORE_PORTS' for t in node.targets)]
    assert len(definitions) == 4
    auditors = {}
    exec(compile(ast.Module(body=definitions, type_ignores=[]), '<frozen-auditors>', 'exec'), auditors)
    models = {label: read(proof / (label + '.json'))['modules'][label] for label in ('gold', 'gate')}
    common, excluded = auditors['state_coverage'](models)
    assert common == result['common_state_names'] and excluded == result['excluded_combinational_names']
    assert (proof / 'blacklist.txt').read_text().splitlines() == excluded
    count = auditors['check_comparisons'](read(proof / 'before.json')['modules']['equivalence'],
                                           read(proof / 'after.json')['modules']['equivalence'], common)
    assert count == 4150 == result['proven_bit_comparisons_including_aliases']
    assert auditors['check_reset'](read(proof / 'reset.json')['modules']['equivalence'], common, count) == result['reset_base']
    assert 'Equivalence successfully proven!' in (proof / 'temporal.log').read_text()
    assert 'SAT proof finished - no model found: SUCCESS!' in (proof / 'reset.log').read_text()
    temporal, reset = ((proof / (n + '.ys')).read_text() for n in ('temporal', 'reset'))
    assert 'equiv_simple; equiv_induct -seq 1; equiv_status -assert;' in temporal
    assert 'sat -verify -seq 2 -set-at 1 rst_n 0 -prove-asserts -prove-skip 1 -set-def-inputs -show-ports' in reset
    controls = read(out / 'controls/result.json')
    assert controls['status'] == 'PASS_BANKED_STORE_PORTS_AND_CHECKED_ALIAS_CONTROLS'
    assert controls['baseline_store_sha256'] == result['sources']['gate']['m1_program_store.v']
    assert controls['bench_sha256'] == sha((out / 'inputs/banked_read_store.sv').read_bytes())
    assert controls['runner_sha256'] == sha((out / 'inputs/run_banked_read_controls.py').read_bytes())
    for simulator in ('icarus', 'verilator'):
        for name in ('parent', 'baseline', 'high-bank-alias'):
            item = controls['runs'][simulator][name]
            work = out / 'controls' / simulator / name
            assert item['compile']['returncode'] == 0 and not item['compile']['timed_out']
            assert not item['simulation']['timed_out']
            assert item['store_sha256'] == sha((work / 'm1_program_store.v').read_bytes())
            assert controls['bench_sha256'] == sha((work / 'banked_read_store.sv').read_bytes())
            log = (work / 'run.log').read_bytes()
            assert item['log_sha256'] == sha(log)
            if name == 'high-bank-alias':
                assert item['status'] == 'EXPECTED_OBSERVABLE_FAILURE' and item['simulation']['returncode'] != 0
                witness = re.search(rb'CHECK_FAILED fetch pc=120 bank=0 observed=([0-9a-f]{8}) expected=([0-9a-f]{8})', log)
                assert witness and int(witness[1], 16) == item['witness']['observed'] != item['witness']['expected'] == int(witness[2], 16)
                assert b'PORT_CHECK_FAILED' in log and b'PASS_STORE_PORT_TEST' not in log
            else:
                assert item['status'] == 'PASS' and item['simulation']['returncode'] == 0
                assert item['checks'] == (1178 if simulator == 'icarus' else 1176)
                assert item['unknown_checks'] == (2 if simulator == 'icarus' else 0)
                assert f'PASS_STORE_PORT_TEST checks={item["checks"]} unknown_checks={item["unknown_checks"]}'.encode() in log
    report = {'status': 'PASS_RETAINED_BANKED_READ_SCREEN', 'files': len(index['files']),
              'store_state_bits': 4109, 'store_output_bits': 54, 'proven_comparison_bits': count,
              'parent_generic_cells': 15211, 'candidate_generic_cells': 15593, 'whole_chip_state_bits': 4278,
              'port_controls': 'PASS_BOTH_SIMULATORS', 'physical': 'NOT_EVALUATED', 'production': 'NOT_PROMOTED'}
    (out / 'verification.json').write_bytes((json.dumps(report, indent=2)+'\n').encode())
    print(json.dumps(report))


if __name__ == '__main__':
    main()
