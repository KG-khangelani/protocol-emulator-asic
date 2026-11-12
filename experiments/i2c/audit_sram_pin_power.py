# SPDX-License-Identifier: Apache-2.0
"""Reject public signal pin shorts and insufficient Metal4 power clearance."""
import argparse
import hashlib
import json
from pathlib import Path
import odb

parser = argparse.ArgumentParser()
parser.add_argument('--odb', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--expect-rejection', action='store_true')
args = parser.parse_args()
out = args.output.resolve()
assert not out.exists() and out.parent.is_dir(), 'new audit directory within the current step required'
out.mkdir()
path = args.odb.resolve()
db = odb.dbDatabase.create()
odb.read_db(db, str(path))
block = db.getChip().getBlock()
assert block.getDbUnitsPerMicron() == 1000
rect = lambda b: (b.xMin(), b.yMin(), b.xMax(), b.yMax())
power = {}
for name in ('VPWR', 'VGND'):
    for wire in block.findNet(name).getSWires():
        for shape in wire.getWires():
            if not shape.isVia():
                power.setdefault(shape.getTechLayer().getName(), []).append((name, rect(shape)))
hits, pins = [], []
for term in sorted(block.getBTerms(), key=lambda t: t.getName()):
    if str(term.getSigType()) in ('POWER', 'GROUND'):
        continue
    for pin in term.getBPins():
        for box in pin.getBoxes():
            layer, bounds = box.getTechLayer().getName(), rect(box)
            pins.append({'pin': term.getName(), 'layer': layer, 'rectangle_dbu': bounds})
            for net, pwr in power.get(layer, []):
                dx = max(bounds[0] - pwr[2], pwr[0] - bounds[2], 0)
                dy = max(bounds[1] - pwr[3], pwr[1] - bounds[3], 0)
                overlap = min(bounds[2], pwr[2]) > max(bounds[0], pwr[0]) and min(bounds[3], pwr[3]) > max(bounds[1], pwr[1])
                gap_bad = layer == 'Metal4' and dx * dx + dy * dy < 420 * 420
                if overlap or gap_bad:
                    hits.append({'pin': term.getName(), 'layer': layer, 'pin_rectangle_dbu': bounds,
                                 'power_net': net, 'power_rectangle_dbu': pwr, 'overlap': overlap,
                                 'separation_dbu': [dx, dy]})
assert len(pins) == 43, len(pins)
result = {'status': 'REJECTED_PUBLIC_PIN_POWER_GEOMETRY' if hits else 'PASS_PUBLIC_PIN_POWER_GEOMETRY',
          'odb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
          'core_rectangle_dbu': rect(block.getCoreArea()), 'pins': pins, 'violations': hits,
          'metal4_minimum_spacing_dbu': 420,
          'scope': 'All public signal pin rectangles vs PDN non-via rectangles, with positive-area overlaps on every layer and 0.42um Metal4 spacing. Other geometry, via enclosures, manufacturing and LVS still require the original full checks.'}
(out / 'result.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
(out / 'runner.py').write_bytes(Path(__file__).read_bytes())
print(result['status'], len(hits), result['core_rectangle_dbu'])
assert bool(hits) == args.expect_rejection, result['status']
