"""Audit the failed official SRAM physical run without accepting its incomplete gates."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
base = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from replay_support import common, physical_sram, Archive, frozen, inspect_runtime
read = lambda p: json.loads(p.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
run, jobs = read(base / 'run.json'), read(base / 'jobs.json')['jobs']
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
    index[label] = {name: sha(archive.bytes(name)) for name in archive.file.namelist() if not name.endswith('/')}
inputs = staged.json('build/sram-physical/inputs.json')
source = run['head_sha']
candidate = json.loads(frozen(source, 'evidence/E0042-sram-prefetch-screen/candidate.json'))
assert inputs['candidate'] == candidate and inputs['workflow_source_commit'] == source
assert inputs['staged_in_ci'] and not inputs['tracked_changes_before_staging']
lock = common.candidate_lock()
assert inputs['flow_lock'] == lock
missing_inputs = []
for name, expected in inputs['provenance_sha256'].items():
    assert sha(frozen(source, name)) == expected
    member = 'build/sram-physical/inputs/' + name
    if member not in index['sram-physical-candidate']:
        missing_inputs.append(name)
    else:
        assert sha(staged.bytes(member)) == expected
assert missing_inputs == ['.github/workflows/gds-sram.yaml'], missing_inputs
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
assert resolved['meta']['flow'] == 'SramBufferedClassic' and not resolved.get('MAGIC_GDS_FLATGLOB')
assert resolved['MAX_TRANSITION_CONSTRAINT'] is None and not resolved['RUN_POST_GRT_DESIGN_REPAIR']
for key in ('RUN_MAGIC_DRC', 'MAGIC_DRC_USE_GDS', 'ERROR_ON_MAGIC_DRC', 'ERROR_ON_ILLEGAL_OVERLAPS', 'ERROR_ON_LVS_ERROR', 'ERROR_ON_PDN_VIOLATIONS', 'ERROR_ON_TR_DRC'):
    assert resolved[key] is True, key
assert resolved['PDK'] == lock['pdk'] and PurePosixPath(resolved['PDK_ROOT']).name == lock['pdk_commit']
assert resolved['meta']['librelane_version'] == lock['librelane']
pdk = {'PDK': resolved['PDK'], 'PDK_VERSION': PurePosixPath(resolved['PDK_ROOT']).name,
       'FLOW_VERSION': resolved['meta']['librelane_version'],
       'evidence': 'Actually resolved configuration and same-job runtime log. No successful-submission metadata exists for this rejected run.'}
workspace = PurePosixPath(resolved['DESIGN_DIR']).parent
def db_bytes(path):
    name = PurePosixPath(path).relative_to(workspace).as_posix()
    assert name.startswith('runs/wokwi/')
    return logs.bytes(name)
power = logs.json('runs/wokwi/23-project-connectsrampower/power-connections.json')
assert power['status'] == 'PASS_GEOMETRY_CONNECTIONS_GRID_CHECK_PENDING' and len(power['added_rectangles']) == 144
assert power['input_odb_sha256'] == sha(db_bytes(logs.json('runs/wokwi/23-project-connectsrampower/state_in.json')['odb']))
grid = logs.json('runs/wokwi/24-project-checksrampower/state_out.json')['metrics']
assert all(grid['design__power_grid_violation__count' + suffix] == 0 for suffix in ('', '__net:VPWR', '__net:VGND'))
buffer = logs.json('runs/wokwi/42-project-buffersraminputs/connectivity-audit.json')
assert buffer['status'] == 'PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY' and buffer['added_buffers'] == 9
for side, state in (('before', 'state_in.json'), ('after', 'state_out.json')):
    assert buffer[side + '_odb_sha256'] == sha(db_bytes(logs.json('runs/wokwi/42-project-buffersraminputs/' + state)['odb']))
drc = logs.bytes('runs/wokwi/65-magic-drc/reports/drc.magic.rpt').decode()
assert '[INFO] COUNT: 58327' in drc
types = {}
category = None
for line in drc.splitlines()[2:]:
    if line.startswith(' ') and 'um' in line:
        assert category
        types[category] += 1
    elif line and not line.startswith(('-', '[INFO]')):
        category = line
        types[category] = 0
assert sum(types.values()) == 58327
lvs = logs.bytes('runs/wokwi/69-netgen-lvs/reports/lvs.netgen.rpt').decode()
assert 'Final result: Top level cell failed pin matching.' in lvs
assert 'Number of nets: 4700 **Mismatch**' in lvs and 'Number of nets: 4717 **Mismatch**' in lvs
bad_json = logs.bytes('runs/wokwi/69-netgen-lvs/reports/lvs.netgen.json')
try:
    json.loads(bad_json)
except json.JSONDecodeError as error:
    assert 'Invalid \\escape' in str(error)
    json_error = {'message': error.msg, 'line': error.lineno, 'column': error.colno}
else:
    raise AssertionError('Expected original invalid JSON is absent')
assert 'runs/wokwi/69-netgen-lvs/state_out.json' not in index['GDS_logs']
assert 'runs/wokwi/final/metrics.json' not in index['GDS_logs']
job = next(j for j in jobs if j['name'] == 'gds')
runtime = inspect_runtime((base / 'gds-job.log').read_bytes(), source, lock, job['id'])
report = {'status': 'PASS_AUDIT_OF_REJECTED_SRAM_PHYSICAL_RUN', 'physical_qualification': 'REJECTED',
    'run_id': run['id'], 'source_commit': source, 'candidate': candidate, 'runtime': runtime, 'pdk': pdk,
    'artifact_files': {name: len(files) for name, files in index.items()},
    'archives': {name: {'id': a.metadata['id'], 'bytes': a.metadata['size_in_bytes'], 'sha256': a.digest} for name, a in archives.items()},
    'drc_count': 58327, 'drc_categories': types,
    'lvs': {'status': 'TOP_LEVEL_PIN_MISMATCH', 'layout_nets': 4700, 'reference_nets': 4717,
            'json_parser_error': json_error, 'raw_report_sha256': sha(bad_json)},
    'power_checks': 'Both grid-continuity checks passed but do not prove absence of public-pin shorts.',
    'native_input_buffer_connectivity': 'PASS_NINE_NATIVE_BUFFERS',
    'precheck': 'SKIPPED', 'official_netlist_test': 'SKIPPED', 'submission': 'NOT_PRODUCED',
    'missing_uploaded_input': missing_inputs,
    'missing_input_boundary': 'Original workflow artifact upload excluded hidden files. The manifest hash matches the exact producing Git commit, but this input is absent from the ZIP. Correct include-hidden-files before the next official qualification.',
    'production': 'NOT_PROMOTED'}
(base / 'verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
(base / 'zip-files.json').write_bytes((json.dumps(index, indent=2) + '\n').encode())
for a in archives.values():
    a.file.close()
print(report['status'], report['drc_count'], report['drc_categories'])
