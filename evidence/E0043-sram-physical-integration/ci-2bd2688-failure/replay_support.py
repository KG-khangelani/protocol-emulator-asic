"""Load only the required frozen audit definitions and immutable observations."""
import ast
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import zipfile

base = Path(sys.argv[1]).resolve()
inputs = base / 'inputs'
def selected(name, definitions, space):
    nodes = []
    for node in ast.parse((inputs / name).read_text()).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in definitions:
            nodes.append(node)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in definitions for t in node.targets):
            nodes.append(node)
    assert len(nodes) == len(definitions)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), space)
    return space

scope = selected('tools/physical_candidate.py', ['require', 'digest', 'read_json', 'candidate_lock', 'verify_run_configuration', 'SIGNOFF_CORNERS'],
                 {'Path': Path, 'hashlib': hashlib, 'json': json, 'ROOT': inputs})
common = SimpleNamespace(**{n: scope[n] for n in ('require', 'digest', 'candidate_lock', 'verify_run_configuration')})
Archive = selected('tools/audit_g2_physical.py', ['Archive'], {'common': common, 'require': common.require, 'zipfile': zipfile, 'json': json})['Archive']
inspect_runtime = selected('tools/physical_runtime.py', ['inspect_runtime'], {'hashlib': hashlib, 're': re})['inspect_runtime']
source = json.loads((base / 'run.json').read_bytes())['head_sha']
def frozen(commit, name):
    assert commit == source
    return (inputs / name).read_bytes()

mapped = (base / 'mapped-input-observation.json').read_bytes()
index = json.loads(frozen(source, 'evidence/E0042-sram-prefetch-screen/mapped/archive.json'))
assert hashlib.sha256(mapped).hexdigest() == index['files']['result.json']
observation = json.loads(mapped)
assert observation['candidate'] == json.loads(frozen(source, 'evidence/E0042-sram-prefetch-screen/candidate.json'))
views = {name.split('/libs.ref/sg13cmos5l_sram/', 1)[1]: metadata for name, metadata in observation['macro_views'].items()}
physical_sram = SimpleNamespace(mapped_macro_views=lambda: views)
