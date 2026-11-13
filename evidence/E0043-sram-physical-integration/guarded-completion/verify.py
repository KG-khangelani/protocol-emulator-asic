# SPDX-License-Identifier: Apache-2.0
"""Verify the completed native failure without replacing its original receipt."""
import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda path: json.loads(path.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
index = read(HERE / 'archive.json')
raw = (HERE / 'reports.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'reports.tar.gz') as archive:
    entries = archive.getmembers()
    assert len(entries) == len(index['files']) and {e.name for e in entries} == set(index['files'])
    for entry in entries:
        path = (out / entry.name).resolve()
        assert entry.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(entry).read()
        assert sha(raw) == index['files'][entry.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
summary = read(out / 'completion-review.json')
assert summary == read(HERE / 'completion-review.json')
receipt = read(out / 'run-result.json')
assert receipt['execution'] == summary['execution']
assert receipt['status'] == 'FAILED_OR_INCOMPLETE' and receipt['execution']['returncode'] == 2
assert not receipt['execution']['timed_out'] and receipt['execution']['seconds'] < receipt['execution']['wall_limit'] == 10800
scope, nodes = {'math': math}, []
for node in ast.parse((out / 'review-inputs/physical_candidate.py').read_text(encoding='utf-8')).body:
    if isinstance(node, ast.FunctionDef) and node.name == 'inspect_physical_metrics':
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SIGNOFF_CORNERS' for t in node.targets):
        nodes.append(node)
assert len(nodes) == 2
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<retained-metric-review>', 'exec'), scope)
run = out / 'runs/integrated'
review = scope['inspect_physical_metrics'](read(run / 'final/metrics.json'))
official = read(out / 'review-inputs/official-verification.json')
assert review == summary['final_physical_metrics'] == official['physical_metrics']
assert review['errors'] == ['magic__drc_error__count: 36 violates zero requirement']
assert sha((run / '66-magic-drc/reports/drc.magic.rpt').read_bytes()) == summary['drc_report_sha256'] == official['drc_report_sha256']
assert sha((run / 'final/nl/tt_um_khangelani_protocol_emulator.nl.v').read_bytes()) == summary['netlist_sha256'] == official['netlist_sha256']
assert 'Final result: Circuits match uniquely.' in (run / '70-netgen-lvs/reports/lvs.netgen.rpt').read_text(encoding='utf-8')
config = read(run / 'resolved.json')
assert config['meta']['flow'] == 'SramGuardedClassic' and config['CLOCK_PERIOD'] == 20
assert config['MAGICRC'].startswith('/pdk/') and not config['meta'].get('substituting_steps')
assert all(config[k] is True for k in ('RUN_MAGIC_DRC', 'MAGIC_DRC_USE_GDS', 'ERROR_ON_MAGIC_DRC', 'ERROR_ON_ILLEGAL_OVERLAPS', 'ERROR_ON_LVS_ERROR'))
assert 'SramGuardedClassic - Stage 84 - Report Manufacturability' in (out / 'run.log').read_text(encoding='utf-8')
geometry = read(HERE.parent / 'ci-2be7f5d-failure/geometry-inputs.json')
gds_path = read(run / '66-magic-drc/state_in.json')['gds'].split('/g2-sram-full-05/', 1)[1]
assert index['omitted_generated_views'][gds_path]['sha256'] == geometry['files']['local-full05.gds']
runtime = read(out / 'runtime-observation.json')
assert runtime['image_id'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
assert summary['status'] == 'COMPLETED_REJECTED_GUARDED_FLOW' and summary['physical_qualification'] == 'REJECTED'
print('PASS_NATIVE_COMPLETION_REPLAY_927_FILES_ORIGINAL_36_FINDINGS_RETAINED')
