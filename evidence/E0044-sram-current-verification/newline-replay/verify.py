"""Replay the real CI counterexample with the old and corrected inspector on this OS."""
import argparse
import ast
import hashlib
import gzip
import json
import os
from pathlib import Path
import subprocess
import zipfile

here = Path(__file__).resolve().parent
root = here.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to(root / 'build')
out.mkdir()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
source = '13660ace269c7b0746d8197fe824f76a5f896934'
path = 'experiments/i2c/run_prefetch_invariant.py'
old = gzip.decompress((here / 'original-inspector.py.gz').read_bytes())
new = gzip.decompress((here / 'corrected-inspector.py.gz').read_bytes())
frame_path = 'experiments/spi_phase/run_program_sensitivity.py'
frames = gzip.decompress((here / 'vcd-parser.py.gz').read_bytes())
expected_hashes = json.loads((here / 'source-hashes.json').read_bytes())
assert {name: sha(raw) for name, raw in [('original', old), ('corrected', new), ('parser', frames)]} == expected_hashes

def function(raw, name, scope):
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), scope)
    return scope[name]

vcd_frames = function(frames, 'vcd_frames', {})
archive = root / 'evidence/E0044-sram-current-verification/ci-13660ac/13986941634.zip'
assert sha(archive.read_bytes()) == '658c32f8474f1fd1afa3a245e1cbb3be6affdb8dcfdd31c4a4345aac6f456108'
with zipfile.ZipFile(archive) as bundle:
    names = [n for n in bundle.namelist() if n.endswith('/prediction/wrong-low-bit/proof/engine_0/trace.vcd')]
    assert len(names) == 1
    prefix = names[0].split('/wrong-low-bit/')[0]
    witness = bundle.read(names[0])
    parsed = bundle.read(prefix + '/wrong-low-bit/parsed-trace.vcd')
    formal = json.loads(bundle.read(prefix + '/result.json'))
expected = [t for t in formal['tasks'] if t['name'] == 'wrong-low-bit'][0]['counterexample']
assert expected
reports = []
for label, code in [('original', old), ('corrected', new)]:
    task = out / label
    (task / 'proof/engine_0').mkdir(parents=True)
    (task / 'proof/engine_0/trace.vcd').write_bytes(witness)
    (task / 'parsed-trace.vcd').write_bytes(parsed)
    (task / 'inspector.py').write_bytes(code)
    inspect = function(code, 'inspect_counterexample', {'vcd_frames': vcd_frames})
    first = inspect(task)
    first_raw = (task / 'parsed-trace.vcd').read_bytes()
    second = inspect(task)
    second_raw = (task / 'parsed-trace.vcd').read_bytes()
    assert first == second == expected
    assert first_raw == second_raw
    assert (task / 'proof/engine_0/trace.vcd').read_bytes() == witness
    stable = first_raw == parsed
    assert stable == (label == 'corrected' or os.name != 'nt')
    reports.append({'inspector': label, 'source_sha256': sha(code), 'observations': first,
                    'parsed_sha256': sha(first_raw), 'unchanged_after_two_inspections': stable})
(out / 'vcd-parser.py').write_bytes(frames)
(out / 'runner.py').write_bytes(Path(__file__).read_bytes())
result = {'status': 'PASS_REAL_COUNTEREXAMPLE_BYTE_PRESERVATION', 'os_name': os.name,
          'source_revision': source, 'original_ci_zip_sha256': sha(archive.read_bytes()),
          'witness_sha256': sha(witness), 'original_parsed_sha256': sha(parsed),
          'original_witness_unchanged': True, 'inspectors': reports,
          'scope': 'Counterexample inspection only; no changed RTL, proof property, solver or interpretation.'}
(out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(json.dumps(result, indent=2))
