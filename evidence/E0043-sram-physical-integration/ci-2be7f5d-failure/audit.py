"""Audit a rejected official run using only its frozen producing definitions."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

base = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_support import common, physical_sram, Archive, frozen, inspect_runtime

read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
run, jobs = read(base / 'run.json'), read(base / 'jobs.json')['jobs']
assert run['id'] == 43320295442 and run['head_sha'] == '2be7f5dcc48fb58c42e27645f2ffe14ab751b9a5'
assert run['status'] == 'completed' and run['conclusion'] == 'failure'
assert run['path'] == '.github/workflows/gds-sram.yaml'
assert {j['name']: j['conclusion'] for j in jobs} == {'gds': 'failure', 'precheck': 'skipped', 'gl_test': 'skipped'}
assert all(j['run_id'] == run['id'] and j['run_attempt'] == run['run_attempt'] and j['status'] == 'completed' for j in jobs)
metadata = read(base / 'artifacts.json')['artifacts']
assert {a['name'] for a in metadata} == {'GDS_logs', 'sram-physical-candidate'}
archives = {a['name']: Archive(base, a, run) for a in metadata}
logs, staged = archives['GDS_logs'], archives['sram-physical-candidate']
index = {}
for label, archive in archives.items():
    assert archive.file.testzip() is None
    index[label] = {n: sha(archive.bytes(n)) for n in archive.file.namelist() if not n.endswith('/')}
inputs = staged.json('build/sram-physical/inputs.json')
source = run['head_sha']
candidate = json.loads(frozen(source, 'evidence/E0042-sram-prefetch-screen/candidate.json'))
assert inputs['candidate'] == candidate and inputs['workflow_source_commit'] == source
assert inputs['staged_in_ci'] and not inputs['tracked_changes_before_staging']
assert 'magic_contact_alignment' not in inputs
lock = common.candidate_lock()
assert inputs['flow_lock'] == lock
for name, expected in inputs['provenance_sha256'].items():
    assert sha(frozen(source, name)) == expected
    assert sha(staged.bytes('build/sram-physical/inputs/' + name)) == expected
for name, expected in inputs['staged_sha256'].items():
    assert sha(staged.bytes(name)) == expected
    if name.startswith('src/'):
        assert sha(logs.bytes(name)) == expected
for name, expected in candidate['source_sha256'].items():
    assert sha(logs.bytes('src/' + name)) == expected
for name, expected in candidate['model_sha256'].items():
    assert sha(staged.bytes('build/sram-physical/candidate/models/' + name)) == expected
assert inputs['macro_views'] == physical_sram.mapped_macro_views()
resolved = logs.json('runs/wokwi/resolved.json')
common.verify_run_configuration(resolved, lock)
assert resolved['meta']['flow'] == 'SramGuardedClassic' and not resolved['meta'].get('substituting_steps')
assert resolved['MAGIC_GDS_FLATGLOB'] == physical_sram.SRAM_IMPORT_PATTERNS
assert resolved['MAX_TRANSITION_CONSTRAINT'] is None and not resolved['RUN_POST_GRT_DESIGN_REPAIR']
assert not resolved.get('MAGIC_DRC_MAGLEFS')
for key in ('RUN_MAGIC_DRC', 'MAGIC_DRC_USE_GDS', 'ERROR_ON_MAGIC_DRC', 'ERROR_ON_ILLEGAL_OVERLAPS',
            'ERROR_ON_LVS_ERROR', 'ERROR_ON_PDN_VIOLATIONS', 'ERROR_ON_TR_DRC'):
    assert resolved[key] is True, key
assert resolved['PDK'] == lock['pdk'] and PurePosixPath(resolved['PDK_ROOT']).name == lock['pdk_commit']
assert resolved['meta']['librelane_version'] == lock['librelane']
workspace = PurePosixPath(resolved['DESIGN_DIR']).parent
assert set(resolved['VERILOG_FILES']) == {str(workspace / 'src' / n) for n in candidate['source_sha256']}
def view(path):
    name = PurePosixPath(path).relative_to(workspace).as_posix()
    assert name.startswith('runs/wokwi/')
    return logs.bytes(name)
stages = {logs.json(n)['meta']['step']: n.rsplit('/', 1)[0] for n in index['GDS_logs']
          if re.fullmatch(r'runs/wokwi/\d+-[^/]+/config.json', n)}
def stage(name):
    directory = stages[name]
    logs.json(directory + '/state_out.json')
    return directory
power = stage('Project.ConnectSramPower')
connections = logs.json(power + '/power-connections.json')
assert connections['status'] == 'PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING' and len(connections['added_rectangles']) == 144
assert connections['input_odb_sha256'] == sha(view(logs.json(power + '/state_in.json')['odb']))
grid = logs.json(stage('Project.CheckSramPower') + '/state_out.json')['metrics']
assert all(grid['design__power_grid_violation__count' + s] == 0 for s in ('', '__net:VPWR', '__net:VGND'))
buffer_dir = stage('Project.BufferSramInputs')
buffers = logs.json(buffer_dir + '/connectivity-audit.json')
assert buffers['status'] == 'PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY' and buffers['added_buffers'] == 9
for side, state in (('before', 'state_in.json'), ('after', 'state_out.json')):
    assert buffers[side + '_odb_sha256'] == sha(view(logs.json(buffer_dir + '/' + state)['odb']))
guard = stage('Project.CheckPublicPinPower')
pins = logs.json(guard + '/pin-power-audit/result.json')
before, after = (logs.json(guard + '/' + s) for s in ('state_in.json', 'state_out.json'))
assert pins['status'] == 'PASS_PUBLIC_PIN_POWER_GEOMETRY' and len(pins['pins']) == 43 and not pins['violations']
assert before['odb'] == after['odb'] and pins['odb_sha256'] == sha(view(before['odb']))
assert pins['metal4_minimum_spacing_dbu'] == 420
assert logs.bytes(guard + '/pin-power-audit/runner.py') == staged.bytes('audit_sram_pin_power.py')
drc_dir = stage('Magic.DRC')
drc_raw = logs.bytes(drc_dir + '/reports/drc.magic.rpt')
assert '[INFO] COUNT: 36' in drc_raw.decode()
categories, category = {}, None
for line in drc_raw.decode().splitlines()[2:]:
    if line.startswith(' ') and 'um' in line:
        assert category
        categories[category] += 1
    elif line and not line.startswith(('-', '[INFO]')):
        category = line
        categories[category] = 0
assert categories == {'N-diffusion overlap of N-diffusion contact < 14 (Cnt.c)': 12,
    'N-diffusion overlap of contact in SRAM < 4 (Cnt.c SRAM exception)': 24}
lvs_dir = stage('Netgen.LVS')
lvs = logs.bytes(lvs_dir + '/reports/lvs.netgen.rpt').decode()
assert 'Final result: Circuits match uniquely.' in lvs and '**Mismatch**' not in lvs
logs.json(lvs_dir + '/reports/lvs.netgen.json')
for name in ('Checker.LVS', 'Checker.IllegalOverlap', 'Checker.SetupViolations', 'Checker.HoldViolations',
             'Checker.MaxSlewViolations', 'Checker.MaxCapViolations', 'Misc.ReportManufacturability'):
    stage(name)
metrics = logs.json('runs/wokwi/final/metrics.json')
review = common.inspect_physical_metrics(metrics)
assert review['status'] == 'FAIL' and review['errors'] == ['magic__drc_error__count: 36 violates zero requirement']
assert metrics['magic__illegal_overlap__count'] == 0
assert 'runs/wokwi/pdk.json' not in index['GDS_logs']
actual_gds = view(logs.json(drc_dir + '/state_in.json')['gds'])
netlist = logs.bytes('runs/wokwi/final/nl/tt_um_khangelani_protocol_emulator.nl.v')
assert netlist == view(logs.json(drc_dir + '/state_in.json')['nl'])
assert sha(netlist) == '2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e'
job = next(j for j in jobs if j['name'] == 'gds')
runtime = inspect_runtime((base / 'gds-job.log').read_bytes(), source, lock, job['id'])
report = {'status': 'PASS_AUDIT_OF_REJECTED_GUARDED_SRAM_PHYSICAL_RUN', 'physical_qualification': 'REJECTED',
    'run_id': run['id'], 'source_commit': source, 'candidate': candidate, 'runtime': runtime,
    'pdk': {'PDK': resolved['PDK'], 'commit': lock['pdk_commit'], 'librelane': lock['librelane'],
        'evidence': 'Actually resolved configuration and same-job runtime; successful-submission pdk.json was not produced.'},
    'artifact_files': {n: len(v) for n, v in index.items()},
    'archives': {n: {'id': a.metadata['id'], 'bytes': a.metadata['size_in_bytes'], 'sha256': a.digest} for n, a in archives.items()},
    'physical_metrics': review, 'drc_count': 36, 'drc_categories': categories,
    'drc_report_sha256': sha(drc_raw), 'checked_gds_sha256': sha(actual_gds), 'netlist_sha256': sha(netlist),
    'lvs': 'CIRCUITS_MATCH_UNIQUELY', 'public_pin_rectangles': 43, 'public_pin_power_violations': 0,
    'native_input_buffers': 9, 'macro_power_bridges': 144, 'missing_uploaded_inputs': [],
    'precheck': 'SKIPPED', 'official_netlist_test': 'SKIPPED', 'submission': 'NOT_PRODUCED', 'production': 'NOT_PROMOTED'}
(base / 'verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
(base / 'zip-files.json').write_bytes((json.dumps(index, indent=2) + '\n').encode())
for archive in archives.values():
    archive.file.close()
print(report['status'], report['artifact_files'], report['physical_metrics']['errors'])
