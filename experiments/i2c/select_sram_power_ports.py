# SPDX-License-Identifier: Apache-2.0
"""Expose only existing full-height supply straps; leave all wires intact."""
import argparse
import hashlib
import json
from pathlib import Path
import re

import odb

sha = lambda raw: hashlib.sha256(raw).hexdigest()
rectangle = lambda b: (b.xMin(), b.yMin(), b.xMax(), b.yMax())


def select_ports(db, directory):
    block = db.getChip().getBlock()
    assert block.getDbUnitsPerMicron() == 1000, 'unexpected database units'
    assert rectangle(block.getDieArea()) == (0, 0, 1724160, 710640), 'unexpected die'
    directory.mkdir(parents=True, exist_ok=False)
    original_def = directory / 'before.def'
    odb.write_def(block, str(original_def))
    plans, rows = [], []
    for name in ('VPWR', 'VGND'):
        term = block.findBTerm(name)
        assert term and str(term.getSigType()) == ('POWER' if name == 'VPWR' else 'GROUND'), 'wrong supply terminal'
        wires = [rectangle(b) for w in term.getNet().getSWires() for b in w.getWires()
                 if not b.isVia() and b.getTechLayer().getName() == 'Metal4']
        kept = 0
        pins = list(term.getBPins())
        assert len(pins) == 1, 'unexpected supply BPin membership'
        for box in pins[0].getBoxes():
            r = rectangle(box)
            assert box.getTechLayer().getName() == 'Metal4', 'wrong supply port layer'
            assert r[2] - r[0] >= 2100, 'undersized supply port'
            assert 0 <= r[0] < r[2] <= 1724160 and 0 <= r[1] < r[3] <= 710640, 'supply port outside die'
            assert any(w[0] <= r[0] and w[1] <= r[1] and w[2] >= r[2] and w[3] >= r[3] for w in wires), 'supply port lacks its real conductor'
            external = r[1] <= 10000 and 710640 - r[3] <= 10000
            rows.append({'net': name, 'rectangle_dbu': r, 'external': external})
            if external:
                kept += 1
            else:
                plans.append(box)
        assert kept == 27, 'expected 27 full-height straps for each supply'
    assert len(plans) == 146 and len(rows) == 200, 'unexpected original supply-port geometry'
    # All rejection conditions above precede the first edit.
    for box in plans:
        odb.dbBox.destroy(box)
    updated_def = directory / 'after.def'
    odb.write_def(block, str(updated_def))
    def split(raw):
        parts = re.split(rb'(?m)^PINS \d+ ;\n|^END PINS\n', raw)
        assert len(parts) == 3, 'unexpected DEF pin section'
        return parts
    before, after = split(original_def.read_bytes()), split(updated_def.read_bytes())
    assert before[0] == after[0] and before[2] == after[2], 'non-pin DEF content changed'
    def signal_pins(raw):
        records = re.split(rb'(?m)^\s*- ', raw)
        return sorted(r for r in records if r.strip() and not r.startswith((b'VPWR ', b'VGND ')))
    assert signal_pins(before[1]) == signal_pins(after[1]), 'public signal pin changed'
    result = {'status': 'PASS_EXISTING_FULL_HEIGHT_POWER_PORT_SELECTION', 'removed_internal_rectangles': len(plans),
              'remaining_external_rectangles': len(rows) - len(plans), 'ports': rows,
              'unchanged_non_pin_def_sha256': sha(before[0] + before[2]),
              'before_def_sha256': sha(original_def.read_bytes()), 'after_def_sha256': sha(updated_def.read_bytes()),
              'scope': 'Only power BPin membership changed; all non-pin DEF bytes and all public signal-pin entries are identical.'}
    (directory / 'selection.json').write_bytes((json.dumps(result, indent=2) + '\n').encode())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--odb', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    db = odb.dbDatabase.create()
    odb.read_db(db, str(args.odb))
    result = select_ports(db, args.output)
    odb.write_db(db, str(args.output / 'selected.odb'))
    print(result['status'], result['removed_internal_rectangles'], result['remaining_external_rectangles'])
