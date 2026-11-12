# SPDX-License-Identifier: Apache-2.0
"""Audit original CI archives, exact source, proof models and public observations."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import tarfile
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile

from proof_checks import check as check_proofs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HEAD = '95120d87c3f09b7598f362f0bb0e66772112d3f7'
RUN = 43287092840
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def selected(path, names, environment):
    chosen = []
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            chosen.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
            chosen.append(node)
    assert len(chosen) == len(names), (path, names)
    exec(compile(ast.Module(body=chosen, type_ignores=[]), str(path), 'exec'), environment)
    return environment


def write_member(base, name, raw):
    path = (base / name).resolve()
    assert path.is_relative_to(base.resolve()) and path != base.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists()
    path.write_bytes(raw)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    out = p.parse_args().output.resolve()
    assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
    out.mkdir(parents=True)
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split('  ', 1)
        assert sha((HERE / name).read_bytes()) == expected, name
    index = read(HERE / 'inputs.json')
    assert index['head'] == HEAD and index['run_id'] == RUN
    raw = (HERE / 'inputs.tar.gz').read_bytes()
    assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
    source = out / 'source'
    with tarfile.open(HERE / 'inputs.tar.gz') as archive:
        members = archive.getmembers()
        assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
        for member in members:
            assert member.isfile()
            raw = archive.extractfile(member).read()
            assert sha(raw) == index['files'][member.name]
            write_member(source, member.name, raw)
    candidate = read(source / 'evidence/E0042-sram-prefetch-screen/candidate.json')
    old = read(source / 'evidence/E0038-shared-program-read/sources/source-manifest.json')['od128']['source_sha256']
    lock = read(source / 'tools/workbench/toolchain.lock.json')['developer_workbench']
    jobs = read(HERE / 'jobs-final.json')['jobs']
    assert len(jobs) == 3 and len({j['id'] for j in jobs}) == 3
    assert all(j['status'] == 'completed' and j['conclusion'] == 'success' and j['run_id'] == RUN for j in jobs)
    assert {j['name'] for j in jobs} == {f'qualify ({g})' for g in ('proof-controls', 'icarus', 'verilator')}
    artifacts = [a for a in read(HERE / 'artifacts-final.json')['artifacts'] if a['name'].startswith('sram-')]
    assert len(artifacts) == 3
    report = {}
    archive_files = 0
    for artifact in artifacts:
        run = artifact['workflow_run']
        assert run['id'] == RUN and run['head_sha'] == HEAD and run['head_branch'] == 'main'
        packed = HERE / (str(artifact['id']) + '.zip')
        assert packed.stat().st_size == artifact['size_in_bytes']
        assert 'sha256:' + sha(packed.read_bytes()) == artifact['digest']
        with zipfile.ZipFile(packed) as archive:
            result = json.loads(archive.read('sram-ci/result.json'))
            gate = result['gate']
            assert artifact['name'] == f'sram-{gate}-{HEAD}' and gate not in report
            assert result['status'] == 'PASS_SRAM_GATE' and result['git_head'] == HEAD and result['candidate'] == candidate
            assert len(archive.namelist()) == len(set(archive.namelist()))
            for member in archive.infolist():
                assert not member.is_dir()
                write_member(out / gate, member.filename, archive.read(member))
            archive_files += len(archive.namelist())
        base = out / gate / 'sram-ci'
        assert read(base / 'candidate/manifest.json') == candidate
        for section, folder in [('source_sha256', 'src'), ('model_sha256', 'models')]:
            for name, expected in candidate[section].items():
                assert sha((base / 'candidate' / folder / name).read_bytes()) == expected
        assert len(result['inputs']) == 33
        for name, expected in result['inputs'].items():
            assert sha((base / 'inputs' / name).read_bytes()) == expected == index['files'][name]
        # Bind every nested proof/regression input copy to the same checkout.
        for child in base.rglob('*'):
            if child.is_file() and 'inputs' in child.relative_to(base).parts and not child.is_relative_to(base / 'inputs'):
                matches = [n for n in result['inputs'] if Path(n).name == child.name]
                if matches:
                    assert len(matches) == 1 and sha(child.read_bytes()) == result['inputs'][matches[0]], str(child)
                else:
                    expected = dict(candidate['source_sha256'], **candidate['model_sha256']).get(child.name)
                    assert expected is not None and sha(child.read_bytes()) == expected, str(child)
        limits = {'engine': 240, 'store-controls': 600, 'store-formal': 1000} if gate == 'proof-controls' else {'regression': 1900}
        assert set(result['stages']) == set(limits)
        for name, limit in limits.items():
            stage = result['stages'][name]
            assert stage['returncode'] == 0 and not stage['timed_out'] and stage['wall_limit'] == limit
            assert 0 < stage['seconds'] < limit
        job = next(j for j in jobs if j['name'] == f'qualify ({gate})')
        log = gzip.decompress((HERE / (str(job['id']) + '.log.gz')).read_bytes()).decode()
        image = read(out / gate / 'sram-runtime/image.json')
        assert len(image) == 1
        image = image[0]
        assert image['Os'] == 'linux' and image['Architecture'] == 'amd64'
        assert lock['image_tag'] in image['RepoTags']
        assert re.search(r'exporting config ' + re.escape(image['Id']) + r' done', log)
        assert f'"containerimage.config.digest": "{image["Id"]}"' in log
        assert f'--tag {lock["image_tag"]} --load' in log
        assert 'docker run --rm --pull=never --init --ulimit core=0' in log
        assert f'--workdir /workspace {lock["image_tag"]}' in log
        assert 'python3 experiments/i2c/run_sram_gate.py --gate "$GATE" --output build/sram-ci' in log
        assert f'GATE: {gate}' in log and f'PASS_SRAM_GATE {gate}' in log
        assert f'{HEAD}:refs/remotes/origin/main' in log
        assert f'SHA256 digest of uploaded artifact is {artifact["digest"].split(":")[1]}' in log
        assert f'Final size is {artifact["size_in_bytes"]} bytes. Artifact ID is {artifact["id"]}' in log
        doctor = (out / gate / 'sram-runtime/doctor.log').read_text(encoding='utf-8')
        assert 'MODE: locked workbench: exact versions required' in doctor and 'RESULT: PASS' in doctor and 'FAIL:' not in doctor
        for name, tool in lock['tools'].items():
            assert f'PASS: {name} ' in doctor and f'  observed: {tool["expected_output"]}' in doctor
        assert lock['python_requirements']['sha256'] in doctor
        assert sha((source / lock['python_requirements']['path']).read_bytes()) == lock['python_requirements']['sha256']
        item = {'job_id': job['id'], 'artifact_id': artifact['id'], 'artifact_sha256': artifact['digest'],
                'files': len(zipfile.ZipFile(packed).namelist()), 'image_id': image['Id'], 'stages': result['stages']}
        if gate == 'proof-controls':
            item['checks'] = check_proofs(base, candidate, old)
        else:
            regression = read(base / 'regression/result.json')
            assert regression['status'] == 'PASS_SRAM_CURRENT_SIMULATOR' and regression['candidate'] == candidate
            assert read(base / 'regression/regenerated/manifest.json') == candidate
            for section, folder in [('source_sha256', 'src'), ('model_sha256', 'models')]:
                for name, expected in candidate[section].items():
                    assert sha((base / 'regression/regenerated' / folder / name).read_bytes()) == expected
            for name, expected in regression['verification_inputs'].items():
                assert sha((base / 'regression/inputs' / name).read_bytes()) == expected == index['files'][name]
            inputs = base / 'inputs'
            common = selected(inputs / 'tools/physical_candidate.py', ['PUBLIC_TESTS', 'PUBLIC_TEST_MODULES', 'EXCLUDED_TESTS', 'require'], {})
            physical = selected(inputs / 'tools/physical_g2.py', ['PUBLIC_TEST_MODULES', 'records', 'check_public_records'],
                                {'common': SimpleNamespace(**common), 'gzip': gzip, 'json': json,
                                 'EVIDENCE': source / 'references', 'require': common['require'], 'digest': lambda p: sha(p.read_bytes())})
            checks = selected(inputs / 'experiments/i2c/run_current_regression.py', ['REQUIRED', 'check_junit', 'check_controls'],
                              {'physical': SimpleNamespace(**physical), 'ET': ET})
            assert len(regression['stages']) == 1
            stage = regression['stages'][0]
            assert stage['simulator'] == gate
            execution = stage['execution']
            assert execution['returncode'] == 0 and not execution['timed_out'] and execution['wall_limit'] == 1800
            assert 0 < execution['seconds'] < 1800
            directory = base / 'regression' / gate
            checked = checks['check_junit'](directory / 'results.xml')
            checked['records'] = physical['check_public_records'](directory / 'records')
            checked['current_bank_control'] = checks['check_controls'](directory / 'records/spi/controls.jsonl')
            assert checked == stage['check'] == read(directory / 'check.json')
            execution_log = (directory / 'run.log').read_text()
            assert ('Running on Icarus Verilog' if gate == 'icarus' else 'Running on Verilator') in execution_log
            assert all(flag in execution_log for flag in ('-DG2_SRAM', '-DFUNCTIONAL', '-DSYNTHESIS'))
            item['checks'] = checked
        report[gate] = item
    summary = {'status': 'PASS_AUDITED_SRAM_CI', 'head': HEAD, 'run_id': RUN, 'archive_files': archive_files,
               'source_files': len(index['files']), 'gates': report, 'physical': 'NOT_EVALUATED', 'production': 'NOT_PROMOTED'}
    (out / 'verification.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
    print(json.dumps({k: v for k, v in summary.items() if k != 'gates'}))


if __name__ == '__main__':
    main()
