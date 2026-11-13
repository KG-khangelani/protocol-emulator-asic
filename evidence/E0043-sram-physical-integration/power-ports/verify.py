# SPDX-License-Identifier: Apache-2.0
"""Verify retained port repair and optionally replay native selection or pin checks."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
read = lambda p: json.loads(p.read_bytes())
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--native', action='store_true')
parser.add_argument('--pins', action='store_true')
parser.add_argument('--dependency-dir', type=Path)
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.is_relative_to((ROOT / 'build').resolve())
for line in (HERE / 'SHA256SUMS').read_text().splitlines():
    expected, name = line.split('  ', 1)
    assert sha((HERE / name).read_bytes()) == expected, name
index = read(HERE / 'archive.json')
bundle = HERE / 'diagnostic.tar.gz'
assert sha(bundle.read_bytes()) == index['sha256'] and bundle.stat().st_size == index['bytes']
out.mkdir(parents=True)
with tarfile.open(bundle) as archive:
    entries = archive.getmembers()
    assert len(entries) == len(index['files']) and {e.name for e in entries} == set(index['files'])
    for entry in entries:
        path = (out / entry.name).resolve()
        assert entry.isfile() and path.is_relative_to(out)
        raw = archive.extractfile(entry).read()
        assert sha(raw) == index['files'][entry.name]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
native = read(HERE / 'native.json')
assert native == read(out / 'probe/native-02/result.json')
assert native['status'] == 'PASS_NATIVE_POWER_PORT_SELECTION_AND_GRID_PIN_DIAGNOSTICS'
assert len(native['stages']) == 4 and all(s['returncode'] == 0 and not s['timed_out'] and s['seconds'] < s['wall_limit'] for s in native['stages'])
selection = native['selection']
assert selection['removed_internal_rectangles'] == 146 and selection['remaining_external_rectangles'] == 54
assert len(selection['ports']) == 200 and sum(p['external'] for p in selection['ports']) == 54
for net in ('VPWR', 'VGND'):
    assert sum(p['net'] == net and p['external'] for p in selection['ports']) == 27
for p in selection['ports']:
    x1, y1, x2, y2 = p['rectangle_dbu']
    assert x2 - x1 >= 2100 and p['external'] == (y1 <= 10000 and 710640 - y2 <= 10000)
before = (out / 'probe/native-02/selection/before.def').read_bytes()
after = (out / 'probe/native-02/selection/after.def').read_bytes()
assert sha(before) == selection['before_def_sha256'] and sha(after) == selection['after_def_sha256']
parts = [re.split(rb'(?m)^PINS \d+ ;\n|^END PINS\n', raw) for raw in (before, after)]
assert all(len(p) == 3 for p in parts)
assert parts[0][0] == parts[1][0] and parts[0][2] == parts[1][2]
assert sha(parts[0][0] + parts[0][2]) == selection['unchanged_non_pin_def_sha256']
signals = lambda raw: sorted(r for r in re.split(rb'(?m)^\s*- ', raw) if r.strip() and not r.startswith((b'VPWR ', b'VGND ')))
assert signals(parts[0][1]) == signals(parts[1][1]) and len(signals(parts[0][1])) == 43
stage = read(HERE / 'staging.json')
assert stage == read(out / 'staging/verification.json') and stage['status'] == 'PASS_PORTABLE_NATIVE_POWER_PORT_STEP'
assert stage['after_def_sha256'] == selection['after_def_sha256'] and len(stage['configuration_controls']) == 2
assert stage['execution']['returncode'] == 0 and not stage['execution']['timed_out']
controls = read(HERE / 'controls.json')
assert controls == read(out / 'probe/native-controls/result.json') and len(controls['cases']) == 4
for case in controls['cases']:
    original = (out / 'probe/native-controls' / (case['case'] + '-input.def')).read_bytes()
    assert original == (out / 'probe/native-controls' / (case['case'] + '-after-rejection.def')).read_bytes()
    assert sha(original) == case['unchanged_input_sha256']
pins = read(HERE / 'pin-check.json')
assert pins == read(out / 'probe/pin-check.json') and pins['status'] == 'PASS_ORIGINAL_REJECTION_AND_SELECTED_POWER_PORTS'
assert pins['gdstk'] == '0.9.52' and pins['numpy'] == '1.26.4'
for name, expected in pins['checker_sha256'].items():
    assert sha((out / 'references' / name).read_bytes()) == expected
for record in (out / 'probe/container-runtime.jsonl').read_text(encoding='utf-8-sig').splitlines():
    runtime = json.loads(record)
    assert runtime['State']['Status'] == 'exited' and runtime['State']['ExitCode'] == 0
    assert runtime['Config']['Image'] in (
        'ghcr.io/librelane/librelane@sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5',
        'protocol-emulator-asic-workbench@sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909')
    assert all(not m['RW'] for m in runtime['Mounts'] if m['Destination'] == '/pdk')
if args.native or args.pins:
    source = HERE.parent / 'ci-232ee20-pin-failure'
    top = 'tt_um_khangelani_protocol_emulator'
    for archive_name, digest, names in (
        ('14000880025.zip', '600d201c57c2719a97254c5a85e13ad0705d496b10c1e131d72fd8e5acadabc0',
         ['runs/wokwi/57-odb-cellfrequencytables/' + top + '.odb']),
        ('14000422018.zip', 'a3e5ff3b6e23c4e44a4b6c676cca47749b0b53f12d47d61df0ec1ce339703c34',
         ['tt_submission/' + top + '.gds'])):
        path = source / archive_name
        assert sha(path.read_bytes()) == digest
        with zipfile.ZipFile(path) as z:
            for name in names:
                target = out / 'probe/original' / Path(name).name
                raw = z.read(name)
                assert sha(raw) == native['input_sha256']['original/' + target.name]
                target.write_bytes(raw)
if args.native:
    r = subprocess.run(['openroad', '-no_init', '-exit', '-python', str(out / 'current/select_sram_power_ports.py'),
         '--odb', str(out / 'probe/original' / (top + '.odb')), '--output', str(out / 'replayed-selection')],
         capture_output=True, timeout=120)
    (out / 'native-replay.log').write_bytes(r.stdout + r.stderr)
    assert r.returncode == 0 and read(out / 'replayed-selection/selection.json') == selection
    assert sha((out / 'replayed-selection/selected.odb').read_bytes()) == stage['output_odb_sha256']
if args.pins:
    assert args.dependency_dir
    sys.path[:0] = [str(out / 'references'), str(args.dependency_dir.resolve())]
    import gdstk
    import numpy
    from pin_check import pin_check
    from precheck_failure import PrecheckFailure
    assert gdstk.__version__ == '0.9.52' and numpy.__version__ == '1.26.4'
    for label, lef in [('original', out / 'probe/original' / (top + '.lef')),
                       ('selected', out / 'probe/native-02/lef/01-magic-writelef' / (top + '.lef'))]:
        try:
            pin_check(str(out / 'probe/original' / (top + '.gds')), str(lef), str(out / 'probe/template.def'), top, False, 'ihp-sg13cmos5l')
        except PrecheckFailure as error:
            assert label == 'original' and '148 LEF errors' in str(error)
        else:
            assert label == 'selected'
print('PASS_RETAINED_POWER_PORT_REPAIR', len(index['files']), 'FILES', 'NATIVE' if args.native else 'PINS' if args.pins else 'REPORTS')
