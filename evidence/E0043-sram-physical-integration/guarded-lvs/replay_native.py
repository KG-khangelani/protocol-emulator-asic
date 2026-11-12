# SPDX-License-Identifier: Apache-2.0
"""Repeat the actual extracted-circuit comparison and check the routed pin geometry."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
from librelane.steps.netgen import get_metrics

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
out = parser.parse_args().directory.resolve()
assert out.is_relative_to(Path('/workspace/build'))
read = lambda p: json.loads(p.read_bytes())
assert read(out / 'verification.json')['status'] == 'PASS_RETAINED_SCOPED_NATIVE_LVS'
run = out / 'passed/run'
native = out / 'native-lvs'
native.mkdir()
initial = read(out / 'passed/initial-state.json')
original_probe = '/workspace/build/g2-sram-guarded-lvs-probe-02/run'
text = (run / '03-netgen-lvs/lvs_script.lvs').read_text()
for before, after in (
    (original_probe + '/01-magic-spiceextraction/tt_um_khangelani_protocol_emulator.spice',
     str(run / '01-magic-spiceextraction/tt_um_khangelani_protocol_emulator.spice')),
    (initial['pnl'], str(run / 'final/pnl/tt_um_khangelani_protocol_emulator.pnl.v')),
    (original_probe + '/03-netgen-lvs/reports/lvs.netgen.rpt', str(native / 'lvs.netgen.rpt')),
):
    assert before in text
    text = text.replace(before, after)
script = native / 'lvs_script.lvs'
script.write_bytes(text.encode())
environment_text = (run / '03-netgen-lvs/_env.tcl').read_text()
environment_text = environment_text.replace(initial['pnl'], str(run / 'final/pnl/tt_um_khangelani_protocol_emulator.pnl.v'))
environment_text = environment_text.replace(original_probe, str(run))
environment_text = environment_text.replace('/workspace/build/g2-sram-full-05', str(out / 'source'))
environment_file = native / '_env.tcl'
environment_file.write_bytes(environment_text.encode())
with (native / 'netgen.log').open('wb') as log:
    command = subprocess.run(['netgen', '-batch', 'source', str(script)], stdout=log, stderr=subprocess.STDOUT,
                             env=dict(os.environ, _TCL_ENV_IN=str(environment_file)), timeout=120)
assert command.returncode == 0
log = (native / 'netgen.log').read_text()
assert 'Circuits match uniquely.' in log
assert not re.search(r'^Error\b|errors reading the setup', log, re.M)
report = read(native / 'lvs.netgen.json')
assert get_metrics(report)['design__lvs_error__count'] == 0
top = report[-1]
assert top['nets'] == [4717, 4717] and not top['badnets'] and not top['badelements']
assert top['pins'][0] == top['pins'][1] and len(top['pins'][0]) == 45
assert all(sum(count for _, count in side) == 4684 for side in top['devices'])
subprocess.run(['openroad', '-no_init', '-exit', '-python', str(out / 'source/portable-pin-audit.py'),
    '--odb', str(run / 'final/odb/tt_um_khangelani_protocol_emulator.odb'),
    '--output', str(out / 'routed-pin-audit')], check=True, timeout=120)
pins = read(out / 'routed-pin-audit/result.json')
assert pins['status'] == 'PASS_PUBLIC_PIN_POWER_GEOMETRY' and len(pins['pins']) == 43 and not pins['violations']
result = {'status': 'PASS_FRESH_NATIVE_CIRCUIT_COMPARISON_AND_ROUTED_PIN_GEOMETRY',
          'matched_nets': 4717, 'matched_devices': 4684, 'matched_pins_including_supplies': 45,
          'routed_public_pin_rectangles': 43, 'routed_pin_power_violations': 0,
          'scope': 'Recompares the retained extracted circuit; does not repeat extraction or full GDS DRC. Original native black-box macro scope preserved.',
          'full_physical_qualification': 'OPEN'}
(out / 'native-verification.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
print(result['status'])
