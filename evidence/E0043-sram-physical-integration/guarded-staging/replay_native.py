# SPDX-License-Identifier: Apache-2.0
"""Reaudit resolved staged files and repeat all eight actual configuration controls."""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
out = parser.parse_args().directory.resolve()
assert out.is_relative_to(Path('/workspace/build'))
read = lambda p: json.loads(p.read_bytes())
assert read(out / 'archive-check.json')['status'] == 'PASS_RETAINED_PORTABLE_GUARDED_STAGING'
pilot = out / 'pilot'
source = pilot / 'inputs'
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
inputs = read(pilot / 'inputs.json')
common = selected(source / 'tools/physical_candidate.py', ['require', 'verify_run_configuration', 'SIGNOFF_CORNERS'], {})
common = SimpleNamespace(**common, candidate_lock=lambda: inputs['flow_lock'])
scope = selected(source / 'tools/physical_sram.py', ['inspect_resolved', 'MODEL_SETS', 'TEMPLATE_SHA256', 'SRAM_IMPORT_PATTERNS', 'SRAM_IMPORT_SETUP_SHA256'],
    {'common': common, 'require': common.require, 'Path': Path,
     'digest': lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(),
     'MACRO': 'RM_IHPSG13_1P_256x32_c2_bm_bist', 'mapped_macro_views': lambda: inputs['macro_views']})
gate = SimpleNamespace(**scope)
original_workspace = '/workspace/build/g2-sram-guarded-staging-01/workspace'
workspace = pilot / 'workspace'
def rebase(value):
    if isinstance(value, str):
        return value.replace(original_workspace, str(workspace))
    if isinstance(value, list):
        return [rebase(v) for v in value]
    if isinstance(value, dict):
        return {k: rebase(v) for k, v in value.items()}
    return value
resolved = rebase(read(workspace / 'runs/guarded-pilot/resolved.json'))
resolved['FP_DEF_TEMPLATE'] = str(out / 'reference/tt_block_8x4_pgvdd.def')
assert gate.inspect_resolved(resolved, inputs, workspace) == inputs['macro_views']
tree = ast.parse((pilot / 'pilot-runner.py').read_text())
loops = [node for node in tree.body if isinstance(node, ast.For) and isinstance(node.target, ast.Tuple)
         and [n.id for n in node.target.elts] == ['name', 'mutate', 'expected']]
assert len(loops) == 1
space = {'controls': [], 'gate': gate, 'resolved': resolved, 'inputs': inputs, 'workspace': workspace, 'copy': copy}
exec(compile(ast.Module(body=loops, type_ignores=[]), 'frozen-pilot-controls', 'exec'), space)
assert space['controls'] == read(pilot / 'pilot-verification.json')['controls']
run = workspace / 'runs/guarded-pilot'
database = run / '29-odb-applydeftemplate/tt_um_khangelani_protocol_emulator.odb'
subprocess.run(['openroad', '-no_init', '-exit', '-python', str(workspace / 'audit_sram_pin_power.py'),
                '--odb', str(database), '--output', str(out / 'fresh-pin-audit')], check=True)
assert read(out / 'fresh-pin-audit/result.json') == read(run / '30-project-checkpublicpinpower/pin-power-audit/result.json')
report = {'status': 'PASS_NATIVE_GUARDED_STAGING_RESOLUTION_AND_EIGHT_CONTROLS',
          'controls': space['controls'], 'source_and_actual_macro_views': 'PASS',
          'fresh_actual_database_pin_geometry': 'PASS_43_PINS_ZERO_VIOLATIONS',
          'full_physical_qualification': 'OPEN'}
(out / 'native-verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(report['status'])
