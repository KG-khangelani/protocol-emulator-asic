"""Measure every actual official DRC marker and compare its physical footprint."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile
import klayout.db as db

base = Path(sys.argv[1]).resolve()
sha = lambda raw: hashlib.sha256(raw).hexdigest()
with zipfile.ZipFile(base / '13994632526.zip') as archive:
    resolved = json.loads(archive.read('runs/wokwi/resolved.json'))
    state = json.loads(archive.read('runs/wokwi/66-magic-drc/state_in.json'))
    name = PurePosixPath(state['gds']).relative_to(PurePosixPath(resolved['DESIGN_DIR']).parent).as_posix()
    raw = archive.read(name)
    report = archive.read('runs/wokwi/66-magic-drc/reports/drc.magic.rpt')
    (base / 'actual-checked.gds').write_bytes(raw)
layout = db.Layout()
layout.read(str(base / 'actual-checked.gds'))
assert layout.dbu == .001
top = layout.cell('tt_um_khangelani_protocol_emulator')
macro_name = 'RM_IHPSG13_1P_256x32_c2_bm_bist'
instances = [i for i in top.each_inst() if i.cell.name == macro_name]
assert len(instances) == 1
transform = instances[0].trans

def boxes(text):
    return [db.Box(*[round(float(v)*1000) for v in re.findall(r'([0-9.]+)um', line)])
            for line in text.splitlines() if line.startswith(' ') and 'um' in line]

markers = boxes(report.decode())
assert len(markers) == 36
isolated_report = (base / 'geometry-inputs/isolated-macro.rpt').read_bytes()
isolated = boxes(isolated_report.decode())
assert len(isolated) == 32
predicted = [box.transformed(transform) for box in isolated]
assert (db.Region(markers) ^ db.Region(predicted)).is_empty(), 'New full-chip error footprint'
observations = []
for marker in markers:
    query = marker.enlarged(1000)
    iterator = top.begin_shapes_rec_overlapping(layout.layer(6, 0), marker)
    contacts = []
    while not iterator.at_end():
        box = iterator.shape().bbox().transformed(iterator.trans())
        if not (db.Region(box) & db.Region(marker)).is_empty():
            contacts.append((box, iterator.cell().name))
        iterator.next()
    assert len({str(box) for box, cell in contacts}) == 1
    contact, cell = contacts[0]
    activ = db.Region(top.begin_shapes_rec_overlapping(layout.layer(1, 0), query)).merged()
    enclosure = max(n for n in range(201) if (db.Region(contact.enlarged(n)) - activ).is_empty())
    coverage = {}
    for name, layer in [('digital', 16), ('sram', 25)]:
        region = db.Region(top.begin_shapes_rec_overlapping(layout.layer(layer, 0), query)).merged()
        coverage[name] = (db.Region(contact) - region).is_empty()
    threshold = 6 if coverage['sram'] else 50 if coverage['digital'] else 70
    assert enclosure >= threshold
    observations.append({'marker_nm': str(marker), 'contact_nm': str(contact), 'source_cell': cell,
        'coincident_contact_occurrences': len(contacts), 'minimum_activ_enclosure_nm': enclosure,
        'marker_coverage': coverage, 'reference_limit_nm': threshold})

local_gds = base / 'geometry-inputs/local-full05.gds'
other = db.Layout()
other.read(str(local_gds))
other_top = other.cell(top.name)
assert other.dbu == layout.dbu
assert set(str(x) for x in layout.layer_infos()) == set(str(x) for x in other.layer_infos())
layers = []
for info in layout.layer_infos():
    a = db.Region(top.begin_shapes_rec(layout.layer(info)))
    b = db.Region(other_top.begin_shapes_rec(other.layer(info)))
    assert (a ^ b).is_empty(), 'Official/local geometry differs on ' + str(info)
    layers.append(str(info))
summary = {'status': 'PASS_ALL_36_OFFICIAL_MARKERS_MATCH_32_ISOLATED_FOOTPRINTS',
    'gds_sha256': sha(raw), 'report_sha256': sha(report), 'isolated_report_sha256': sha(isolated_report),
    'macro_transform': str(transform), 'isolated_marker_count': 32, 'official_marker_count': 36,
    'unique_contact_count': len({o['contact_nm'] for o in observations}),
    'marker_footprint_xor': 'EMPTY', 'observations': observations,
    'local_full05_gds_sha256': sha(local_gds.read_bytes()), 'official_local_shape_xor_layers': layers,
    'official_local_shape_xor': 'EMPTY_ALL_LAYERS',
    'scope': 'Diagnostic measurement of unchanged geometry against pinned reference rules. Original official run remains rejected; no report filtering or count waiver.',
    'full_physical_qualification': 'OPEN'}
out = base / 'contact-geometry.json'
assert not out.exists()
out.write_bytes((json.dumps(summary, indent=2) + '\n').encode())
print(summary['status'], summary['unique_contact_count'], len(layers))
