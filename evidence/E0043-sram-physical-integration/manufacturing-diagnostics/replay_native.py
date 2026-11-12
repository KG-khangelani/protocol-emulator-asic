# SPDX-License-Identifier: Apache-2.0
"""Replay the actual old/corrected geometry and both corrected power-grid checks."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
out = parser.parse_args().directory.resolve()
assert out.is_relative_to(Path('/workspace/build'))
read = lambda p: json.loads(p.read_bytes())
assert read(out / 'archive-check.json')['status'] == 'PASS_RETAINED_MANUFACTURING_DIAGNOSIS'
assert not (out / 'verification.json').exists()
pilot = out / 'core-grid'
corrected = pilot / 'runs/fixed-pins/05-odb-applydeftemplate/tt_um_khangelani_protocol_emulator.odb'
for name, database, rejected, reference in (
    ('original', out / 'original-routed.odb', True, out / 'old-clearance-control/result.json'),
    ('corrected', corrected, False, out / 'corrected-clearance/result.json'),
):
    command = ['openroad', '-no_init', '-exit', '-python', str(out / 'native-pin-check.py'), '--odb', str(database), '--output', str(out / ('replayed-' + name))]
    if rejected:
        command.append('--expect-rejection')
    with (out / (name + '-replay.log')).open('wb') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
    actual, expected = read(out / ('replayed-' + name) / 'result.json'), read(reference)
    assert actual == {k: v for k, v in expected.items() if k != 'state_sha256'}
script = out / 'recheck-grids.tcl'
script.write_bytes(('read_db {' + str(corrected) + '}\n' + ''.join(
    'check_power_grid -net ' + name + ' -error_file {' + str(out / (name + '-grid.rpt')) + '}\nputs {PASS_SRAM_GRID ' + name + '}\n' for name in ('VPWR', 'VGND'))).encode())
start = time.monotonic()
with (out / 'recheck-grids.log').open('wb') as log:
    subprocess.run(['openroad', '-no_init', '-exit', str(script)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
log = (out / 'recheck-grids.log').read_text()
assert all('PASS_SRAM_GRID ' + name in log and 'All shapes on net ' + name + ' are connected.' in log for name in ('VPWR', 'VGND'))
report = {'status': 'PASS_NATIVE_PUBLIC_PIN_AND_POWER_GRID_REPLAY', 'original_pin_overlaps': 17,
          'original_clearance_violations': 24, 'corrected_pin_rectangles': 43, 'corrected_geometry_violations': 0,
          'corrected_database_sha256': hashlib.sha256(corrected.read_bytes()).hexdigest(),
          'fresh_grid_checks': ['VPWR', 'VGND'], 'grid_seconds': round(time.monotonic() - start, 3),
          'full_physical_acceptance': 'OPEN'}
(out / 'verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
print(report['status'])
