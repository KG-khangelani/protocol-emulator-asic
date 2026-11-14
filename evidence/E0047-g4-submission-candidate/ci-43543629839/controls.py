# SPDX-License-Identifier: Apache-2.0
"""Attempt semantic and provenance corruption against an actual passing archive set."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path.cwd().resolve()
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
write = lambda p,v: p.write_bytes((json.dumps(v, indent=2) + '\n').encode())
parser = argparse.ArgumentParser()
parser.add_argument('--base', type=Path, required=True)
parser.add_argument('--audit', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
base, out, audit = (p.resolve() for p in (args.base, args.output, args.audit))
assert base.is_relative_to(ROOT / 'build') and out.is_relative_to(ROOT / 'build') and not out.exists()
baseline = read(base / 'audit/result.json')
assert baseline['status'] == 'PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES'
out.mkdir(parents=True)
results = []
cases = [('pending-workflow', None, 'physical workflow is not successfully complete'),
         ('wrong-archive-digest', None, 'archive digest mismatch'),
         ('rehashed-port-count', 'GDS_logs', 'power-port selection differs'),
         ('rehashed-skipped-test', 'gatelevel_test_results', 'required public test skipped'),
         ('rehashed-netlist', 'tt_submission', 'submitted netlist differs'),
         ('wrong-job-source', None, 'G4 job source differs'),
         ('rehashed-production', 'sram-physical-candidate', 'production verification differs'),
         ('rehashed-stage-configuration', 'GDS_logs', 'G4 executed stage configuration differs'),
         ('rehashed-stage-skip', 'GDS_logs', 'configured G4 stage sequence differs')]
for label, changed_archive, expected_error in cases:
    directory = out / label
    directory.mkdir()
    run, jobs, metadata = (read(base / n) for n in ('run.json', 'jobs.json', 'artifacts.json'))
    if label == 'pending-workflow':
        run.update(status='in_progress', conclusion=None)
    if label == 'wrong-archive-digest':
        next(a for a in metadata['artifacts'] if a['name'] == 'GDS_logs')['digest'] = 'sha256:' + '0' * 64
    if label == 'wrong-job-source':
        jobs['jobs'][0]['head_sha'] = '0' * 40
    mutation = None
    for a in metadata['artifacts']:
        if a['name'] not in baseline['archives']:
            continue
        name = str(a['id']) + '.zip'
        original, target = base / name, directory / name
        if a['name'] != changed_archive:
            os.link(original, target)
            continue
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(target, 'w') as dest:
            if label == 'rehashed-port-count':
                matches = [n for n in source.namelist() if n.endswith('/power-port-audit/selection.json')]
                assert len(matches) == 1
                member = matches[0]
                before = source.read(member)
                data = json.loads(before)
                assert data['remaining_external_rectangles'] == 54
                data['remaining_external_rectangles'] = 53
                after = (json.dumps(data, indent=2) + '\n').encode()
            elif label == 'rehashed-skipped-test':
                member = 'results.xml'
                before = source.read(member)
                data = ET.fromstring(before)
                selected = data.find('.//testcase[@name="complete_i2c_transactions"]')
                assert selected is not None and selected.find('skipped') is None
                ET.SubElement(selected, 'skipped')
                after = ET.tostring(data)
            elif label == 'rehashed-production':
                member = 'build/sram-physical/inputs.json'
                before = source.read(member)
                data = json.loads(before)
                data['production']['qualified_run_id'] += 1
                after = (json.dumps(data, indent=2) + '\n').encode()
            elif label == 'rehashed-stage-configuration':
                member = 'runs/wokwi/01-verilator-lint/config.json'
                before = source.read(member)
                data = json.loads(before)
                data['meta']['step'] = 'Unqualified.Stage'
                after = (json.dumps(data, indent=2) + '\n').encode()
            elif label == 'rehashed-stage-skip':
                member = 'runs/wokwi/flow.log'
                before = source.read(member)
                expected = b"Gating variable for step 'OpenROAD.RepairDesignPostGRT' set to 'False'"
                assert before.count(expected) == 1
                after = before.replace(expected, expected.replace(b"'False'", b"'True'"))
            else:
                member = 'tt_submission/tt_um_khangelani_protocol_emulator.v'
                before = source.read(member)
                after = before + b'\n// deliberately changed submitted circuit control\n'
            for item in source.infolist():
                dest.writestr(item, after if item.filename == member else source.read(item.filename))
        a['size_in_bytes'] = target.stat().st_size
        a['digest'] = 'sha256:' + sha(target.read_bytes())
        mutation = {'archive': changed_archive, 'member': member,
                    'before_sha256': sha(before), 'after_sha256': sha(after),
                    'rehashed_archive_sha256': a['digest'], 'metadata_rehashed_for_semantic_control': True}
    write(directory / 'run.json', run)
    write(directory / 'jobs.json', jobs)
    write(directory / 'artifacts.json', metadata)
    for name in ('gds', 'precheck', 'gl_test'):
        os.link(base / (name + '-job.log'), directory / (name + '-job.log'))
    result = subprocess.run([sys.executable, str(audit), '--directory', str(directory),
        '--output', str(directory / 'audit')], cwd=ROOT, capture_output=True, timeout=300)
    log = result.stdout + result.stderr
    (directory / 'audit.log').write_bytes(log)
    observed = read(directory / 'audit/result.json')
    assert result.returncode != 0 and observed['status'] == 'NOT_QUALIFIED', label
    assert observed['error'] == expected_error, (label, observed)
    results.append({'name': label, 'status': 'PASS_REJECTED_CORRUPTION', 'returncode': result.returncode,
        'expected_error': expected_error, 'observed': observed, 'mutation': mutation, 'log_sha256': sha(log)})
    print('PASS_REJECTED_CORRUPTION', label)
write(out / 'result.json', {'status': 'PASS_NINE_COMPLETE_QUALIFICATION_FAULT_CONTROLS',
    'baseline_result_sha256': sha((base / 'audit/result.json').read_bytes()),
    'audit_sha256': sha(audit.read_bytes()), 'runner_sha256': sha(Path(__file__).read_bytes()),
    'run_id': baseline['run_id'], 'source_commit': baseline['source_commit'], 'cases': results})
