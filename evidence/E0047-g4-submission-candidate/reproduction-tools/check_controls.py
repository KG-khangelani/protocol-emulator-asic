"""Validate timestamp-only normalization against the real retained G2 GDS."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
out.mkdir(parents=True)
gds = module('g4_gds', HERE / 'compare_gds_records.py')
audit = module('g4_reproduce', HERE.parent / 'reproduce.py')
original = ROOT / 'evidence/E0045-g2-sram-qualification/ci-94a3082/14004891901.zip'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
with zipfile.ZipFile(original) as z:
    raw = z.read('tt_submission/tt_um_khangelani_protocol_emulator.gds')
assert sha(raw) == '51ac3c1005fd0d811a3e26fddf81fd996a2d57b45172a68670df05e4c57dbbf4'
base = out / 'original.gds'
base.write_bytes(raw)
_, records = audit.checked_records(gds, base)
offset, timestamp_offset, geometry_offset = 0, None, None
for length, kind, datatype, value in records:
    if kind == 0x01 and timestamp_offset is None:
        timestamp_offset = offset
    if kind == 0x10 and datatype == 3 and geometry_offset is None:
        geometry_offset = offset
    offset += length
assert timestamp_offset is not None and geometry_offset is not None
cases = []
for name, index, permitted in (
        ('timestamp-only', timestamp_offset + 7, True),
        ('geometry-coordinate', geometry_offset + 7, False)):
    changed = bytearray(raw)
    changed[index] ^= 1
    path = out / (name + '.gds')
    path.write_bytes(changed)
    audit.checked_records(gds, path)
    result = gds.compare(base, path)
    assert result['equivalent_except_timestamps'] is permitted
    cases.append({'name': name, 'status': 'PASS_ACCEPTED_ONLY_TIMESTAMP_CHANGE' if permitted else 'PASS_REJECTED_GEOMETRY_CHANGE',
                  'changed_byte': index, 'original_sha256': sha(raw), 'changed_sha256': sha(changed),
                  'equivalent_except_timestamps': result['equivalent_except_timestamps']})
changed = bytearray(raw)
changed[timestamp_offset + 3] = 3
path = out / 'timestamp-wrong-datatype.gds'
path.write_bytes(changed)
try:
    audit.checked_records(gds, path)
except ValueError as error:
    assert str(error) == 'unexpected GDS timestamp record format'
else:
    raise AssertionError('non-date payload could be hidden as timestamps')
cases.append({'name': 'timestamp-wrong-datatype', 'status': 'PASS_REJECTED_NON_DATE_NORMALIZATION',
              'changed_byte': timestamp_offset + 3, 'changed_sha256': sha(changed)})
result = {'schema': 'protocol-emulator-g4-gds-controls-v1', 'status': 'PASS_THREE_GDS_COMPARISON_CONTROLS',
          'source_run_id': 43348171110, 'original_submission_zip_sha256': sha(original.read_bytes()),
          'comparator_sha256': sha((HERE / 'compare_gds_records.py').read_bytes()),
          'runner_sha256': sha(Path(__file__).read_bytes()), 'reproduction_auditor_sha256': sha((HERE.parent / 'reproduce.py').read_bytes()),
          'cases': cases, 'scope': 'Auditor controls on original G2 layout; not a fresh G4 physical result.'}
(out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(result['status'])
