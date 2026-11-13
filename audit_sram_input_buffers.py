# SPDX-License-Identifier: Apache-2.0
"""Check actual OpenDB connectivity before/after nine native SRAM buffers."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import odb

PINS = [*(f'A_ADDR[{i}]' for i in range(7)), 'A_WEN', 'A_DIN[15]']


def inspect(path):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    return db, db.getChip().getBlock()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--before', required=True, type=Path)
    p.add_argument('--after', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    before_db, before = inspect(args.before)
    after_db, after = inspect(args.after)
    original = {i.getName(): i for i in before.getInsts()}
    updated = {i.getName(): i for i in after.getInsts()}
    # The native insertion API treats its name arguments as prefixes and
    # appends a unique numeric suffix; bind each actual load independently.
    added = set(updated) - set(original)
    buffer_names = {}
    for index in range(9):
        names = [n for n in added if re.fullmatch(f'sram_input_buffer_{index}[0-9]+', n)]
        assert len(names) == 1, (index, names)
        buffer_names[index] = names[0]
    buffers = set(buffer_names.values())
    assert len(buffers) == 9 and set(updated) == set(original) | buffers
    assert all(updated[n].getMaster().getName() == original[n].getMaster().getName() for n in original)
    assert all(updated[n].getMaster().getName() == 'sg13cmos5l_buf_4' for n in buffers)
    original_nets = {n.getName(): n for n in before.getNets()}
    updated_nets = {n.getName(): n for n in after.getNets()}
    macro_before, macro_after = before.findInst('store.program_memory'), after.findInst('store.program_memory')
    net_names = {i: macro_after.findITerm(name).getNet().getName() for i, name in enumerate(PINS)}
    assert all(re.fullmatch(f'sram_buffered_input_{i}[0-9]+', name) for i, name in net_names.items()), ('TARGET_NET_IDENTITY_CHANGED', net_names)
    new_nets = set(net_names.values())
    assert len(new_nets) == 9 and set(updated_nets) == set(original_nets) | new_nets and not set(original_nets) & new_nets
    assert macro_before.getLocation() == macro_after.getLocation()
    assert str(macro_before.getOrient()) == str(macro_after.getOrient())
    identify = lambda pin: (pin.getInst().getName(), pin.getMTerm().getName())
    restored = {n: {identify(t) for t in net.getITerms() if t.getInst().getName() not in buffers}
                for n, net in updated_nets.items() if n not in new_nets}
    rows = []
    for index, name in enumerate(PINS):
        buffer = updated[buffer_names[index]]
        old_net = macro_before.findITerm(name).getNet().getName()
        new_net = updated_nets[net_names[index]]
        assert buffer.findITerm('A').getNet().getName() == old_net, ('BUFFER_INPUT_CHANGED', name)
        assert buffer.findITerm('X').getNet().getName() == new_net.getName()
        assert macro_after.findITerm(name).getNet().getName() == new_net.getName()
        assert {identify(t) for t in new_net.getITerms()} == {
            (buffer.getName(), 'X'), ('store.program_memory', name)}
        assert not new_net.getBTerms()
        assert buffer.findITerm('VDD').getNet().getName() == 'VPWR'
        assert buffer.findITerm('VSS').getNet().getName() == 'VGND'
        restored[old_net].add(('store.program_memory', name))
        rows.append({'pin': name, 'original_net': old_net, 'buffer': buffer.getName(),
                     'new_net': new_net.getName(), 'buffer_location_dbu': buffer.getLocation()})
    for name, net in original_nets.items():
        assert restored[name] == {identify(t) for t in net.getITerms()}, name
        assert {t.getName() for t in net.getBTerms()} == {t.getName() for t in updated_nets[name].getBTerms()}, name
        assert str(net.getSigType()) == str(updated_nets[name].getSigType())
    pin_identity = lambda block: sorted((t.getName(), str(t.getIoType()), str(t.getSigType()),
        sorted((s.getTechLayer().getName(), s.xMin(), s.yMin(), s.xMax(), s.yMax())
               for pin in t.getBPins() for s in pin.getBoxes())) for t in block.getBTerms())
    assert pin_identity(before) == pin_identity(after)
    moved = [n for n in original if original[n].getLocation() != updated[n].getLocation()
             or str(original[n].getOrient()) != str(updated[n].getOrient())]
    result = {'status': 'PASS_NINE_NATIVE_BUFFERS_COLLAPSE_TO_ORIGINAL_CONNECTIVITY',
              'before_odb_sha256': hashlib.sha256(args.before.read_bytes()).hexdigest(),
              'after_odb_sha256': hashlib.sha256(args.after.read_bytes()).hexdigest(),
              'original_instances': len(original), 'added_buffers': 9,
              'original_instances_moved_by_native_legalization': moved, 'connections': rows,
              'physical_qualification': 'NOT_EVALUATED'}
    args.output.write_bytes((json.dumps(result, indent=2) + '\n').encode())
    print(result['status'])


if __name__ == '__main__':
    main()
