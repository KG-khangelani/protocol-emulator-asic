# SPDX-License-Identifier: Apache-2.0
"""Replay both actual-netlist suites and the explicit reset-model compatibility probe."""
import argparse
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def selected(path, names, space):
    nodes = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            nodes.append(node)
    assert len(nodes) == len(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), space)
    return space


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    index = read(HERE / 'archive.json')
    raw = (HERE / 'netlist.tar.gz').read_bytes()
    assert len(raw) == index['bytes'] and sha(raw) == index['sha256']
    with tarfile.open(HERE / 'netlist.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            path = (out / member.name).resolve()
            assert member.isfile() and path.is_relative_to(out)
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    candidate = read(out / 'candidate.json')
    assert candidate == read(ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json')
    assert {name: sha((out / 'source' / name).read_bytes()) for name in candidate['source_sha256']} == candidate['source_sha256']
    common = selected(out / 'icarus/inputs/tools/physical_candidate.py',
                      ['PUBLIC_TESTS', 'PUBLIC_TEST_MODULES', 'EXCLUDED_TESTS', 'require'], {})
    checks = selected(out / 'icarus/inputs/tools/physical_g2.py',
                      ['PUBLIC_TEST_MODULES', 'records', 'check_public_records', 'check_tests'],
                      {'common': SimpleNamespace(**common), 'gzip': gzip, 'json': json, 'ET': ET,
                       'EVIDENCE': out / 'references', 'require': common['require'],
                       'digest': lambda p: sha(p.read_bytes()),
                       'write_json': lambda p, v: p.write_bytes((json.dumps(v, indent=2, sort_keys=True) + '\n').encode())})
    summaries, identities = {}, []
    for simulator in ('icarus', 'verilator'):
        path = out / simulator
        result = read(path / 'result.json')
        assert result['status'] == 'PASS_SRAM_ACTUAL_NETLIST_PUBLIC_SELECTION'
        assert result['candidate'] == candidate and result['simulator'] == simulator
        assert result['evidence_kind'] == 'FUNCTIONAL_ZERO_DELAY_NETLIST' and result['physical_qualification'] == 'SEPARATE_GATE'
        assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
        assert result['execution']['seconds'] < result['execution']['wall_limit'] == 10800
        assert result['doctor']['returncode'] == 0 and 'RESULT: PASS' in (path / 'doctor.log').read_text()
        assert sha((path / 'netlist.v').read_bytes()) == result['netlist_sha256']
        assert sha((out / 'physical/post-pnr-state.json').read_bytes()) == result['physical_state_sha256']
        for name, expected in result['inputs'].items():
            assert sha((path / 'inputs' / name).read_bytes()) == expected
        for name, expected in candidate['model_sha256'].items():
            assert sha((path / 'models' / name).read_bytes()) == expected
        text = (path / 'netlist.v').read_text()
        assert len(re.findall(r'RM_IHPSG13_1P_256x32_c2_bm_bist\s+\\store\.program_memory\s', text)) == 1
        assert not re.search(r'\b(always|initial)\s*(@|begin)', text)
        flops = re.findall(r'^\s*(sg13cmos5l_(?:df|dl[hl])[a-z0-9_]+)\s+', text, re.M)
        assert len(flops) == 353 and set(flops) == {'sg13cmos5l_dfrbpq_1'}
        checks['check_tests'](SimpleNamespace(junit=path / 'results.xml', records=path / 'records',
                                             output=out / (simulator + '-recheck.json'), require_netlist=False))
        checked = read(out / (simulator + '-recheck.json'))
        assert checked == read(path / 'check.json')
        checked.update(variant='od128-sram', netlist_sha256=result['netlist_sha256'], evidence_kind='FUNCTIONAL_ZERO_DELAY_NETLIST')
        assert checked == result['checks']
        log = (path / 'run.log').read_text()
        assert ('Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator') in log
        assert all(flag in log for flag in ('-DGL_TEST', '-DG2_SRAM', '-DFUNCTIONAL', '-DSYNTHESIS', '20261112'))
        assert all(name in log for name in result['library_sha256'])
        assert not any('/src/' + name in log for name in candidate['source_sha256'])
        runtime = read(path / 'completed-runtime.json')
        assert runtime['image_id'] == runtime['configured_image'] == 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
        assert runtime['state']['Status'] == 'exited' and runtime['state']['ExitCode'] == 0
        assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
        identities.append((result['netlist_sha256'], result['library_sha256'], result['inputs']))
        summaries[simulator] = {'groups': 18, 'seconds': result['execution']['seconds'], 'records': result['checks']['records']}
    assert identities[0] == identities[1]
    stop = read(out / 'physical/deliberate-stop.json')
    assert stop['status'] == 'DECLARED_STOP_OF_KNOWN_INVALID_POWER_GEOMETRY'
    assert stop['pin_geometry_audit_sha256'] == sha((out / 'physical/pin-geometry-audit.json').read_bytes())
    assert stop['after']['Status'] == 'exited' and stop['after']['ExitCode'] == 137
    physical_scope = read(out / 'physical/scope.json')
    assert physical_scope['physical_status'] == 'REJECTED_PUBLIC_PIN_POWER_SHORTS'
    assert physical_scope['known_public_pin_power_overlaps'] == 17
    original = read(out / 'verilator-warning-failure/result.json')
    failed = read(out / 'verilator-reset-failure/result.json')
    for label, result in [('verilator-warning-failure', original), ('verilator-reset-failure', failed)]:
        assert result['status'] == 'FAILED_OR_INCOMPLETE' and result['execution']['returncode'] == 2
        assert not result['execution']['timed_out']
        assert result['netlist_sha256'] == identities[0][0] and result['library_sha256'] == identities[0][1]
        assert sha((out / label / 'netlist.v').read_bytes()) == identities[0][0]
    warnings = (out / 'verilator-warning-failure/run.log').read_text()
    assert Counter(re.findall(r'%Warning-([^:]+):', warnings)) == {'SPECIFYIGN': 84, 'PINMISSING': 28}
    lines = (out / 'icarus/netlist.v').read_text().splitlines()
    loads = set()
    for lineno, port in re.findall(r"%Warning-PINMISSING: [^:\n]+:(\d+):\d+: Instance has missing pin: '([^']+)'", warnings):
        match = re.fullmatch(r'\s*sg13cmos5l_(inv|buf)_\d+ (clkload\d+) \(\.A\((clknet_[^)]+)\)\);', lines[int(lineno) - 1])
        assert match and port == ('Y' if match[1] == 'inv' else 'X')
        loads.add(match[2])
    assert loads == {'clkload' + str(i) for i in range(28)}
    assert not (out / 'verilator-warning-failure/results.xml').exists()
    failures = ET.parse(out / 'verilator-reset-failure/results.xml').getroot().findall('.//testcase[failure]')
    assert len(failures) == 18
    required = {(module, name) for name, module in checks['PUBLIC_TEST_MODULES'].items()}
    assert {(c.get('classname'), c.get('name')) for c in failures} == required
    probe = out / 'reset-probe'
    result = read(probe / 'result.json')
    assert result['status'] == 'PASS_ZERO_DELAY_RESET_ALIAS_WITH_UNMODIFIED_ICARUS_REFERENCE_AND_STUCK_RESET_CONTROL'
    assert [t['name'] for t in result['tasks']] == ['original-icarus', 'original-verilator', 'reset-alias-verilator', 'wrong-reset-alias-verilator']
    assert [t['mismatches'] for t in result['tasks']] == [0, 249, 0, 249]
    samples_by_task = {}
    for task in result['tasks']:
        assert task['accepted'] and task['observations'] == 1025
        for command in ('compile', 'run'):
            assert task[command]['returncode'] == 0 and not task[command]['timed_out']
        samples = re.findall(r'^CELL_SAMPLE (.*)$', (probe / task['name'] / 'run.log').read_text(), re.M)
        assert len(samples) == 1025 and sha(('\n'.join(samples) + '\n').encode()) == task['samples_sha256']
        expected, old_clk, mismatches = 0, 0, 0
        for index_, line in enumerate(samples):
            row = list(map(int, line.split()))
            count, bench_expected, actual, direct, clk, d, reset_b, delayed_clk, delayed_d, delayed_reset = row
            assert count == index_ and delayed_clk == clk and delayed_d == d
            if not reset_b:
                expected = 0
            elif not old_clk and clk:
                expected = d
            assert bench_expected == direct == expected
            mismatches += actual != expected
            old_clk = clk
            assert delayed_reset == (0 if task['expected_failure'] else reset_b)
        assert mismatches == task['mismatches']
        samples_by_task[task['name']] = samples
    assert samples_by_task['original-icarus'] == samples_by_task['reset-alias-verilator']
    adapter = (probe / 'reset-alias.sv').read_bytes()
    assert sha(adapter) == result['adapter_sha256']
    assert adapter.replace(b'= reset_b;', b"= 1'b0;") == (probe / 'wrong-reset-alias.sv').read_bytes()
    review = read(out / 'verilator/reset-alias-review.json')
    assert review['status'] == 'PASS_IDENTICAL_NETLIST_WITH_EXPLICIT_ZERO_DELAY_RESET_ALIAS'
    assert review['actual_affected_flip_flops'] == 353 and review['actual_returncode'] == 0
    assert review['netlist_sha256'] == identities[0][0] and review['library_sha256'] == identities[0][1]
    assert review['adapter_sha256'] == sha(adapter) and (out / 'verilator/reset-alias.sv').read_bytes() == adapter
    assert review['microprobe_sha256'] == sha((probe / 'result.json').read_bytes())
    assert review['flags'] == ['-Wno-SPECIFYIGN', '-Wno-PINMISSING']
    assert 'no functional role was false' in review['correction']
    assert review['adapter_path'] in (out / 'verilator/run.log').read_text()
    assert '%Warning-' not in (out / 'verilator/run.log').read_text()
    result = {'status': 'PASS_RETAINED_IDENTICAL_NETLIST_PAIR_WITH_EXPLICIT_RESET_ALIAS',
              'files': len(index['files']), 'netlist_sha256': identities[0][0], 'simulators': summaries,
              'cell_observations': 1025, 'original_and_stuck_reset_mismatches': 249,
              'failed_public_groups_before_alias': 18, 'adapter_sha256': sha(adapter),
              'physical_scope': physical_scope,
              'boundary': 'Pinned zero-delay digital model compatibility; not four-state equivalence, extracted timing, manufacturing or official precheck acceptance.'}
    (out / 'verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'], result['files'])


if __name__ == '__main__':
    main()
