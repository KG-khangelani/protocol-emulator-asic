"""Remeasure G2's historical failure sites in both submitted G4 GDS payloads."""
from collections import Counter
from contextlib import ExitStack
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tarfile

import klayout.db as db
from inspect_retained import source_archive


MACRO = "RM_IHPSG13_1P_256x32_c2_bm_bist"


def references():
    base = Path("evidence/E0043-sram-physical-integration/contact-rules")
    index = json.loads((base/"archive.json").read_bytes())
    archive = base/"diagnostic.tar.gz"
    if sha256(archive.read_bytes()).hexdigest() != index["sha256"]:
        raise ValueError("bad original diagnosis archive digest")
    with tarfile.open(archive) as tar:
        def raw(key):
            data = tar.extractfile(key).read()
            if sha256(data).hexdigest() != index["files"][key]:
                raise ValueError(f"bad digest for {key}")
            return data
        report = raw("original-macro/reports/drc.magic.rpt").decode()
        old = json.loads(raw("geometry/result.json"))
        deck = raw("reference/libs.tech/klayout/tech/drc/rule_decks/feol/5_14_cont.drc")
        params = json.loads(raw("reference/libs.tech/klayout/tech/drc/rule_decks/sg13cmos5l_tech_default.json"))["drc_rules"]
    rules_nm = {k: round(float(params[k])*1000) for k in ("Cnt_c", "Cnt_c_sram", "Cnt_c_digibnd", "grid")}
    if not all(rule.encode() in deck for rule in ("Cnt_c_sram", "Cnt_c_digibnd", "Cnt_c")):
        raise ValueError("missing contact rule")
    markers = [db.Box(*(round(float(n)*1000) for n in re.findall(r"([0-9.]+)um", line)))
               for line in report.splitlines() if line.startswith(" ")]
    if len(set(str(m) for m in markers)) != 32:
        raise ValueError("unexpected original site count")
    return markers, old["observations"], rules_nm


def count_contacts(cell, layer, marker):
    it = cell.begin_shapes_rec_overlapping(layer, marker)
    boxes = []
    while not it.at_end():
        box = it.shape().bbox().transformed(it.trans())
        if not (db.Region(box) & db.Region(marker)).is_empty():
            boxes.append(box)
        it.next()
    if len({str(b) for b in boxes}) != 1:
        raise ValueError(f"ambiguous contact site {marker}")
    return boxes[0], len(boxes)


def measure(layout, markers, rules):
    cell = layout.cell(MACRO)
    if cell is None or layout.dbu != .001:
        raise ValueError("missing macro or unexpected units")
    findings = []
    for marker in markers:
        contact, multiplicity = count_contacts(cell, layout.layer(6,0), marker)
        area = contact.enlarged(350)
        def region(layer):
            return db.Region(cell.begin_shapes_rec_overlapping(layout.layer(layer,0), area)).merged()
        active = region(1)
        flags = {k: (db.Region(contact) - region(layer)).is_empty() for k, layer in (("digital",16),("sram",25))}
        # Binary-search the last n for which the whole expanded box is covered.
        lo, hi = 0, 300
        if not (db.Region(contact)-active).is_empty() or (db.Region(contact.enlarged(hi))-active).is_empty():
            raise ValueError("search interval did not bracket the tightest enclosure")
        while hi-lo > 1:
            mid = (lo+hi)//2
            if (db.Region(contact.enlarged(mid))-active).is_empty():
                lo = mid
            else:
                hi = mid
        limit = rules["Cnt_c_sram"] if flags["sram"] else rules["Cnt_c_digibnd"] if flags["digital"] else rules["Cnt_c"]
        findings.append({"marker_nm": str(marker), "contact_nm": str(contact), "minimum_activ_enclosure_nm": lo,
                         "marker_coverage": flags, "reference_limit_nm": limit, "coincident_contact_occurrences": multiplicity})
    return findings


def submitted(directory, markers, rules):
    result = json.loads((directory/"result.json").read_bytes())
    key = "tt_submission/tt_um_khangelani_protocol_emulator.gds"
    with ExitStack() as stack:
        archive = stack.enter_context(source_archive(directory, result, "tt_submission"))
        image = archive.read(key)
        if sha256(image).hexdigest() != result["gds_sha256"]:
            raise ValueError("submitted GDS digest mismatch")
        # Keep the large uncompressed layout in process memory. KLayout reads the descriptor.
        stream = stack.enter_context(os.fdopen(os.memfd_create("submitted-g4.gds"), "w+b"))
        stream.write(image)
        stream.seek(0)
        layout = db.Layout()
        layout.read(f"/proc/self/fd/{stream.fileno()}")
        measured = measure(layout, markers, rules)
    return measured, {"run": result["run_id"], "gds_sha256": result["gds_sha256"]}


if __name__ == "__main__":
    markers, historical, rules = references()
    root = Path("evidence/E0047-g4-submission-candidate")
    records = [submitted(root/f"ci-{n}", markers, rules) for n in (43543626249,43543629839)]
    first = records[0][0]
    if first != records[1][0]:
        raise ValueError("submitted GDS geometries disagree at the failure sites")
    old = {row["marker_nm"]: row for row in historical}
    if any(v != old[r["marker_nm"]][k] for r in first for k,v in r.items()):
        raise ValueError("fresh geometry disagrees with isolated original macro")
    observed = Counter((r["minimum_activ_enclosure_nm"], r["reference_limit_nm"]) for r in first)
    if observed != Counter({(60,50):12, (10,6):20}):
        raise ValueError("actual enclosure distribution changed")
    strict = sum(r["marker_coverage"]["sram"] and r["minimum_activ_enclosure_nm"] < 15 for r in first)
    if strict != 20:
        raise ValueError("hypothetical stricter SRAM threshold failed to discriminate")
    print(json.dumps({"klayout": db.__version__, "units": "nm", "rules_and_grid": rules,
                      "actual_enclosure_and_reference_limit": {f"{a}/{b}":n for (a,b),n in observed.items()},
                      "hypothetical_15nm_sram_threshold_rejects": strict, "runs": [r[1] for r in records],
                      "measured": first}, indent=2))
