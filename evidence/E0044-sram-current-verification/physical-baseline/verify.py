# SPDX-License-Identifier: Apache-2.0
"""Check frozen configuration generation and all nine unchanged source profiles."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
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
raw = (HERE / 'rehearsal.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'rehearsal.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    for member in members:
        path = (out / member.name).resolve()
        assert member.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(member).read()
        assert sha(raw) == index['files'][member.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
result = read(out / 'result.json')
assert result == read(HERE / 'result.json')
assert result['status'] == 'PASS_NINE_PHYSICAL_PROFILES_IDENTICAL_CONFIGURATIONS_AND_RTL'
reference = out / 'reference'
baseline = (reference / 'src/config.json').read_bytes()
lock = read(out / 'tested-inputs/tools/workbench/toolchain.lock.json')['official_cmos5l_8x4']
assert sha(baseline) == result['baseline_sha256'] == lock['config_sha256_lf']
assert baseline == (out / 'tested-inputs/experiments/physical/d34-config.json').read_bytes()
expected = read(out / 'expected-candidates.json')
assert set(result['profiles']) == set(expected) and len(expected) == 9
def require(condition, message):
    assert condition, message
scope = {'ROOT': reference, 'read': read, 'require': require, 'MACRO': 'RM_IHPSG13_1P_256x32_c2_bm_bist'}
nodes = []
for node in ast.parse((reference / 'tools/physical_sram.py').read_text(encoding='utf-8')).body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('MODEL_SETS', 'SRAM_IMPORT_PATTERNS') for t in node.targets):
        nodes.append(node)
    if isinstance(node, ast.FunctionDef) and node.name == 'portable_config':
        nodes.append(node)
assert len(nodes) == 3
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<original-configuration-generator>', 'exec'), scope)
variants = {'g1-P': 'P', 'g1-compact10': 'compact10', 'g2-od128': 'od128',
            'g2-literal255': 'literal255', 'g2-lanes': 'od128', 'g2-shared': 'od128'}
for label, observation in result['profiles'].items():
    profile = out / label
    inputs = read(profile / 'inputs.json')
    assert inputs['config_source_path'] == 'experiments/physical/d34-config.json'
    assert observation['source_sha256'] == expected[label]
    if label in variants:
        source = profile / 'variants' / variants[label] / 'src'
        config = profile / 'config.json'
        assert config.read_bytes() == baseline
        assert inputs['source_sha256'] == expected[label]
    else:
        source = profile / 'workspace/src'
        config = source / 'config.json'
        assert inputs['candidate']['source_sha256'] == expected[label]
        original = scope['portable_config'](scope['MACRO'] + '.vh',
            guarded=label != 'sram-buffered', aligned=label == 'sram-aligned')
        assert config.read_bytes() == (json.dumps(original, indent=2, sort_keys=True) + '\n').encode()
        for name, digest in observation['staged_sha256'].items():
            assert sha((profile / 'workspace' / name).read_bytes()) == digest
        for name, digest in observation['model_sha256'].items():
            assert sha((profile / 'candidate/models' / name).read_bytes()) == digest
    assert sha(config.read_bytes()) == observation['config_sha256']
    assert {name: sha((source / name).read_bytes()) for name in expected[label]} == expected[label]
log = (out / 'repository-check.log').read_bytes()
assert sum(map(int, re.findall(rb'Ran (\d+) tests?', log))) == 118
assert log.count(b'\nOK\n') == 12 and b'FAILED' not in log
print('PASS_358_FILES_NINE_UNCHANGED_PHYSICAL_PROFILES_118_REPOSITORY_TESTS')
