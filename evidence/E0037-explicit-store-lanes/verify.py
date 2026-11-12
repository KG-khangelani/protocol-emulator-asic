# SPDX-License-Identifier: Apache-2.0
"""Replay D38 evidence: every retained byte, complete store proof and public records."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'experiments/i2c'))
from audit_store_proofs import audit
from tools import physical_g2 as physical


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to((ROOT / 'build').resolve()) and not out.exists(), 'new build output required'
    out.mkdir(parents=True)
    index = read(HERE / 'archives.json')
    assert set(index) == {'store', 'selection'}
    sources = read(HERE / 'sources/source-manifest.json')['od128']['source_sha256']
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
        assert physical.verify_sources(target / 'variants/od128/src', 'od128-lanes') == sources
        expected = 'PASS_LANES_AUDITED_STORE' if gate == 'store' else 'PASS_LANES_PUBLIC_SELECTION'
        assert read(target / 'result.json')['status'] == expected

    proof = out / 'store/store'
    proof_result = read(proof / 'result.json')
    assert proof_result['status'] == 'PASS_SELECTED_STORE_TASKS'
    assert sha((proof / 'runner.py').read_bytes()) == proof_result['runner_sha256']
    for task in proof_result['tasks']:
        directory = proof / task['directory']
        dest = directory / 'proof/src'
        dest.mkdir(parents=True, exist_ok=True)
        if task['name'] in ('state', 'read'):
            shutil.copyfile(proof / 'od128-model/prepared.il', dest / 'prepared.il')
        else:
            shutil.copyfile(directory / 'store.v', dest / 'store.v')
    expected = read(out / 'store/audit/od128.json')
    observed = audit(proof, proof, 'od128', (out / 'store/audit/od128.positive.json').read_bytes(), 'explicit-lanes')
    assert observed == {k:v for k,v in expected.items() if k != 'positive_checkpoint'}
    controls = read(out / 'store/audit/auditor-controls.json')
    assert controls['status'] == 'PASS_AUDITOR_NEGATIVE_CONTROLS' and len(controls['controls']) == 9
    assert all(c['rejected'] for c in controls['controls'])

    selection = out / 'selection/selection'
    result = read(selection / 'result.json')
    assert result['status'] == 'PASS_G2_PHYSICAL_SELECTION_ON_BOTH_RTL_SIMULATORS'
    assert result['sources'] == sources and [s['simulator'] for s in result['stages']] == ['icarus', 'verilator']
    checks = {}
    for stage in result['stages']:
        simulator = stage['simulator']
        path = selection / simulator
        assert stage['returncode'] == 0
        identity = 'Running on Icarus Verilog' if simulator == 'icarus' else 'Running on Verilator'
        assert identity in (path / 'run.log').read_text()
        checked = out / (simulator + '-public.json')
        physical.check_tests(SimpleNamespace(junit=path / 'results.xml', records=path / 'records',
                                            output=checked, require_netlist=False))
        assert read(checked) == stage['check'] == read(path / 'check.json')
        checks[simulator] = {'public_test_groups': 18, 'records': stage['check']['records'],
                             'junit_sha256': sha((path / 'results.xml').read_bytes())}
    old = read(ROOT / 'evidence/E0035-general-i2c/sources/current/source-manifest.json')['od128']['source_sha256']
    assert {k:v for k,v in sources.items() if k != 'm1_program_store.v'} == {k:v for k,v in old.items() if k != 'm1_program_store.v'}
    equivalence = read(ROOT / 'evidence/E0036-g2-store-and-ci/lane-screen/equivalence/result.json')
    eq = next(t for t in equivalence['tasks'] if t['variant'] == 'od128')
    assert eq['accepted'] and eq['before_sha256'] == old['m1_program_store.v'] and eq['after_sha256'] == sources['m1_program_store.v']
    style = read(HERE / 'style/result.json')
    assert style['status'] == 'PASS_SCOPED_STYLE_REVIEW' and style['sources'] == sources
    assert [s['name'] for s in style['stages']] == ['other-modules', 'store-unwaived', 'store-scoped']
    for stage in style['stages']:
        raw = gzip.decompress((HERE / 'style' / (stage['name'] + '.log.gz')).read_bytes())
        assert sha(raw) == stage['log_sha256']
        if stage['name'] == 'store-unwaived':
            assert stage['returncode'] == 1 and len(raw.splitlines()) == 128
            assert all(line.endswith(b'[Style: case-statements] [case-missing-default]') for line in raw.splitlines())
        else:
            assert stage['returncode'] == 0
    report = {'status': 'PASS_LANES_CANDIDATE_RTL_FORMAL', 'implementation': 'od128-lanes', 'source_sha256': sources,
              'program_words': 128, 'program_bits': 4096, 'store_assertions': observed['assertions'],
              'positive_store_tasks': observed['positive_task_count'], 'checked_reset_reachable_controls': 2,
              'public_simulators': checks, 'archives': {k:v['archive_sha256'] for k,v in index.items()},
              'style_review': {'status': style['status'], 'unwaived_warnings': 128,
                               'exception': style['exception'], 'result_sha256': sha((HERE / 'style/result.json').read_bytes())},
              'inherited_evidence': 'Byte-identical engine/support modules retain E0035/E0036 instruction proofs; E0036 od128 complete-store equivalence links the rewritten store',
              'physical': 'NOT_YET_QUALIFIED', 'production': 'UNCHANGED',
              'scope': 'Local complete public regression and memory-unit properties; no arbitrary-firmware, analog, or physical signoff'}
    if (HERE / 'qualification.json').exists():
        assert report == read(HERE / 'qualification.json')
    (out / 'qualification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
    print(report['status'])


if __name__ == '__main__':
    main()
