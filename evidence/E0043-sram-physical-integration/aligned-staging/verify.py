# SPDX-License-Identifier: Apache-2.0
"""Check retained portable staging bytes and their actual native pilot results."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
index = read(HERE / 'archive.json')
raw = (HERE / 'staging.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'staging.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    for member in members:
        path = (out / member.name).resolve()
        assert member.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(member).read()
        assert sha(raw) == index['files'][member.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
pilot = out / 'pilot'
inputs = read(pilot / 'inputs.json')
template = gzip.decompress((HERE / 'tt_block_8x4_pgvdd.def.gz').read_bytes())
assert sha(template) == inputs['template_sha256']
(out / 'reference/tt_block_8x4_pgvdd.def').write_bytes(template)
for name, expected in inputs['provenance_sha256'].items():
    assert sha((pilot / 'inputs' / name).read_bytes()) == expected
for name, expected in inputs['staged_sha256'].items():
    assert sha((pilot / 'workspace' / name).read_bytes()) == expected
candidate = inputs['candidate']
for name, expected in candidate['model_sha256'].items():
    assert sha((pilot / 'candidate/models' / name).read_bytes()) == expected
assert candidate == read(ROOT / 'evidence/E0042-sram-prefetch-screen/candidate.json')
report = read(pilot / 'pilot-verification.json')
assert report == read(HERE / 'verification.json')
assert report['status'] == 'PASS_PORTABLE_ALIGNED_PILOT_AND_TWELVE_CONFIGURATION_CONTROLS'
assert report['execution']['returncode'] == 0 and not report['execution']['timed_out']
assert report['execution']['wall_limit'] == 300 and report['execution']['seconds'] < 300
assert len(report['controls']) == len({c['fault'] for c in report['controls']}) == 12
run = pilot / 'workspace/runs/aligned-pilot'
guard = run / '30-project-checkpublicpinpower'
pins = read(guard / 'pin-power-audit/result.json')
assert pins == read(out / 'reference/public-pin-audit.json')
assert pins['status'] == 'PASS_PUBLIC_PIN_POWER_GEOMETRY' and not pins['violations'] and len(pins['pins']) == 43
before, after = read(guard / 'state_in.json'), read(guard / 'state_out.json')
assert before['odb'] == after['odb']
database = run / '29-odb-applydeftemplate/tt_um_khangelani_protocol_emulator.odb'
assert sha(database.read_bytes()) == pins['odb_sha256'] == report['actual_odb_sha256']
grid = read(run / '24-project-checksrampower/state_out.json')['metrics']
assert all(grid['design__power_grid_violation__count' + suffix] == 0 for suffix in ('', '__net:VPWR', '__net:VGND'))
runtime = read(out / 'runtime.json')
assert runtime['image_id'] == runtime['configured_image'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
assert runtime['state']['ExitCode'] == 0 and not runtime['state']['Running']
assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
result = {'status': 'PASS_RETAINED_PORTABLE_ALIGNED_STAGING', 'files': len(index['files']),
          'actual_database_sha256': pins['odb_sha256'], 'public_pin_rectangles': 43,
          'recorded_configuration_controls': 12, 'native_configuration_replay': 'REQUIRED_SEPARATELY',
          'full_physical_qualification': 'OPEN'}
(out / 'archive-check.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(result['status'], result['files'])
