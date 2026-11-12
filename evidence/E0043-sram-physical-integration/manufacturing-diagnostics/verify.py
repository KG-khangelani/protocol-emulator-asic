# SPDX-License-Identifier: Apache-2.0
"""Verify the retained import controls and the real pin/power geometry diagnosis."""
import argparse
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
raw = (HERE / 'diagnostics.tar.gz').read_bytes()
assert sha(raw) == index['sha256'] and len(raw) == index['bytes']
with tarfile.open(HERE / 'diagnostics.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    for member in members:
        path = (out / member.name).resolve()
        assert member.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(member).read()
        assert sha(raw) == index['files'][member.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
for label in ('macro-original-timeout', 'macro-vendor-timeout'):
    result = read(out / label / 'result.json')
    assert result['status'] == 'INCOMPLETE_OR_FAILED_MACRO_DIAGNOSTIC'
    assert result['execution']['timed_out'] and result['execution']['returncode'] == 124
    assert result['execution']['wall_limit'] == 120 and 'reported_count' not in result
assert read(out / 'macro-wrong-target/result.json')['status'] == 'REJECTED_WRONG_DIAGNOSTIC_TARGET'
assert read(out / 'macro-preflight-01/result.json')['status'] == 'FAILED_BEFORE_MAGIC_LAUNCH'
pair = read(out / 'import-pair/result.json')
assert pair['target'] == 'RM_IHPSG13_1P_BITKIT_16x2_SRAM'
assert [t['label'] for t in pair['tasks']] == ['original', 'vendor-import', 'narrow-metal-control']
assert [t['count'] for t in pair['tasks']] == [232, 0, 1]
assert all(t['execution']['returncode'] == 0 and not t['execution']['timed_out'] and t['execution']['seconds'] < 120 for t in pair['tasks'])
scripts = [(out / 'import-pair' / t['label'] / 'drc.tcl').read_bytes() for t in pair['tasks']]
assert scripts[0] == scripts[1]
assert sha(scripts[0]) == '815c0ada08d55bb0b3b5c84cd80e0620590897b7f3e8e3c7c3d3f117bbe1f74b'
assert scripts[2] == scripts[1].replace(b'select top cell\ndrc euclidean on', b'select top cell\nbox values 1000um 1000um 1000.05um 1000.05um\npaint metal2\ndrc euclidean on')
assert 'Metal2 minimum area' in (out / 'import-pair/narrow-metal-control/reports/drc.magic.rpt').read_text()
assert sha((out / 'import-pair/read_sram_gds.tcl').read_bytes()) == '5a818473a3ffad96d84e1f72331fbb94c46cc1df24a01bc9d8367ac3a7211cd7'
patterns = [line.split()[2] for line in (out / 'import-pair/read_sram_gds.tcl').read_text().splitlines() if line.startswith('gds flatglob ')]
assert patterns == pair['patterns'] and len(patterns) == 7
bad = read(out / 'old-clearance-control/result.json')
good = read(out / 'corrected-clearance/result.json')
assert bad['status'] == 'REJECTED_PUBLIC_PIN_POWER_GEOMETRY' and len(bad['violations']) == 24
assert sum(v['overlap'] for v in bad['violations']) == 17
assert good['status'] == 'PASS_PUBLIC_PIN_POWER_GEOMETRY' and not good['violations']
assert good['pins'] == bad['pins'] and len(good['pins']) == 43
assert sha((out / 'original-routed.odb').read_bytes()) == bad['odb_sha256']
pilot = out / 'core-grid'
corrected = pilot / 'runs/fixed-pins/05-odb-applydeftemplate/tt_um_khangelani_protocol_emulator.odb'
assert sha(corrected.read_bytes()) == good['odb_sha256']
before = (pilot / 'inputs/original-pdn.tcl').read_text().splitlines()
after = (pilot / 'src/sram_pdn.tcl').read_text().splitlines()
assert after == [line.removesuffix(' -extend_to_boundary') if line.startswith('add_pdn_stripe -grid stdcell_grid -layer Metal4 ') else line for line in before]
assert sum(a != b for a, b in zip(before, after)) == read(pilot / 'inputs/core-grid-decision.json')['changed_stripe_commands']
run = read(pilot / 'run-result.json')
assert run['status'] == 'COMMAND_SUCCEEDED_REQUIRES_ARTIFACT_AUDIT' and run['execution']['returncode'] == 0 and not run['execution']['timed_out']
assert run['execution']['seconds'] == 38.405 and run['execution']['wall_limit'] == 300
grid = read(pilot / 'runs/integrated/24-project-checksrampower/state_out.json')['metrics']
assert all(grid['design__power_grid_violation__count' + suffix] == 0 for suffix in ('', '__net:VPWR', '__net:VGND'))
pin_run = read(out / 'fixed-pins/result.json')
assert pin_run['status'] == 'PASS_NATIVE_CORE_GRID_AND_FIXED_PUBLIC_PIN_CLEARANCE'
assert pin_run['execution']['returncode'] == pin_run['geometry_execution']['returncode'] == 0
for name in ('g2-sram-full-03', 'g2-sram-full-04'):
    stopped = read(out / 'stopped' / name / 'deliberate-stop.json')
    assert stopped['status'] == 'DECLARED_STOP_OF_KNOWN_INVALID_POWER_GEOMETRY'
    assert not stopped['after']['Running'] and stopped['after']['ExitCode'] != 0
for path in (out / 'runtime').glob('*.json'):
    runtime = read(path)
    assert runtime['image_id'] == runtime['configured_image'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert not runtime['state']['Running']
early = (out / 'runtime/g2-sram-core-pdn-clearance-01.log').read_text()
assert 'AssertionError: 0' in early
report = {'status': 'PASS_RETAINED_MANUFACTURING_DIAGNOSIS', 'files': len(index['files']),
          'subcell_original_errors': 232, 'subcell_vendor_import_errors': 0, 'injected_metal_errors': 1,
          'original_pin_overlaps': 17, 'original_clearance_violations': 24,
          'corrected_pin_rectangles': 43, 'corrected_geometry_violations': 0,
          'power_pilot_seconds': 38.405, 'native_replay': 'REQUIRED_SEPARATELY', 'full_physical_acceptance': 'OPEN'}
(out / 'archive-check.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(report['status'], report['files'])
