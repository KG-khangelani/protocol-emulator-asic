# SPDX-License-Identifier: Apache-2.0
"""Bind the retained scoped LVS result to the actual unchanged corrected design."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

here = Path(__file__).resolve().parent
root = here.parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
out = parser.parse_args().output.resolve()
assert not out.exists() and out.is_relative_to(root / 'build')
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
index = read(here / 'archive.json')
raw = (here / 'diagnostic.tar.gz').read_bytes()
assert len(raw) == index['bytes'] and sha(raw) == index['sha256']
with tarfile.open(here / 'diagnostic.tar.gz') as archive:
    members = archive.getmembers()
    assert len(members) == len(index['files']) and {m.name for m in members} == set(index['files'])
    for member in members:
        path = (out / member.name).resolve()
        assert member.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(member).read()
        assert sha(raw) == index['files'][member.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
source = out / 'source'
candidate = read(out / 'candidate.json')
assert candidate == read(root / 'evidence/E0042-sram-prefetch-screen/candidate.json')
assert {n: sha((source / 'src' / n).read_bytes()) for n in candidate['source_sha256']} == candidate['source_sha256']
result = read(out / 'passed/result.json')
assert result['status'] == 'PASS_SCOPED_NATIVE_EXTRACTION_AND_LVS'
assert result['full_physical_qualification'] == 'OPEN'
assert result['execution']['returncode'] == 0 and not result['execution']['timed_out']
assert result['execution']['seconds'] < result['execution']['wall_limit'] == 600
assert result['config_sha256'] == sha((source / 'src/config_merged.json').read_bytes())
assert result['resolved_sha256'] == sha((source / 'original-resolved.json').read_bytes())
assert result['initial_state_sha256'] == sha((out / 'passed/initial-state.json').read_bytes())
initial = read(out / 'passed/initial-state.json')
run = out / 'passed/run'
for key, expected in result['input_view_sha256'].items():
    files = [p for p in (run / 'final' / key).iterdir() if p.is_file()]
    assert len(files) == 1 and sha(files[0].read_bytes()) == expected
def_identity = read(here / 'def-input-identity.json')
assert def_identity['initial_state_sha256'] == result['initial_state_sha256']
assert def_identity['actual_input_path'] == initial['def']
assert def_identity['actual_input_sha256'] == sha((run / 'final/def/tt_um_khangelani_protocol_emulator.def').read_bytes())
assert ('set ::env(CURRENT_DEF) ' + initial['def']) in (run / '01-magic-spiceextraction/_env.tcl').read_text()
final = run / '04-checker-lvs/state_out.json'
assert sha(final.read_bytes()) == result['final_state_sha256']
metrics = read(final)['metrics']
assert metrics['design__lvs_error__count'] == metrics['magic__illegal_overlap__count'] == 0
resolved = read(run / 'resolved.json')
assert resolved == read(source / 'original-resolved.json')
assert resolved['ERROR_ON_LVS_ERROR'] and resolved['ERROR_ON_ILLEGAL_OVERLAPS']
assert resolved['MAGIC_EXT_USE_GDS'] is False
report = read(run / '03-netgen-lvs/reports/lvs.netgen.json')
top = report[-1]
assert top['name'] == ['tt_um_khangelani_protocol_emulator'] * 2
assert top['nets'] == [4717, 4717] and top['pins'][0] == top['pins'][1] and len(top['pins'][0]) == 45
assert not top['badnets'] and not top['badelements']
assert all(sum(count for _, count in side) == 4684 for side in top['devices'])
assert 'Circuits match uniquely.' in (run / '03-netgen-lvs/netgen-lvs.log').read_text()
assert '-blackbox -json' in (run / '03-netgen-lvs/lvs_script.lvs').read_text()
failed = read(out / 'launch-error/result.json')
assert failed['execution']['returncode'] == 2 and not failed['execution']['timed_out']
assert "Invalid value for '--force-run-dir'" in (out / 'launch-error/run.log').read_text()
for label, exitcode in [('launch-error', 1), ('passed', 0)]:
    runtime = read(out / label / 'runtime.json')
    assert runtime['image_id'] == runtime['configured_image'] == 'sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5'
    assert runtime['state']['Status'] == 'exited' and runtime['state']['ExitCode'] == exitcode
    assert any(m['Destination'] == '/pdk' and not m['RW'] for m in runtime['mounts'])
summary = {'status': 'PASS_RETAINED_SCOPED_NATIVE_LVS', 'files': len(index['files']),
    'seconds': result['execution']['seconds'], 'matched_nets': 4717, 'matched_devices': 4684,
    'matched_top_level_pins_including_supplies': 45, 'lvs_errors': 0, 'illegal_overlaps': 0,
    'layout_netlist_sha256': sha((run / '01-magic-spiceextraction/tt_um_khangelani_protocol_emulator.spice').read_bytes()),
    'reference_netlist_sha256': result['input_view_sha256']['pnl'],
    'scope': 'Original native DEF/LEF extraction and black-box macro LVS; not internal transistor LVS of the vendor macro or full GDS manufacturing qualification.',
    'full_physical_qualification': 'OPEN'}
(out / 'verification.json').write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(summary['status'], summary['files'])
