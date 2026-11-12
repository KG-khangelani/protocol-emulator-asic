# SPDX-License-Identifier: Apache-2.0
"""Stage the bounded Cnt.c correction without modifying the pinned PDK."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

REFERENCE_SHA256 = {
    "libs.tech/magic/ihp-sg13cmos5l.magicrc": "55c49b71d2bcd6e7d3dccbbbe1d6a246070bebf514b48df32d1a1394cab02b26",
    "libs.tech/magic/ihp-sg13cmos5l.tech": "c7d8b4b716f5602e20905a1250a2d7d924fc8aff0a10a9b910535a6eb46c6404",
    "libs.tech/magic/ihp-sg13cmos5l-cifin.tech": "f3c452eec8ad396a033e507cbd61ed2d67246255b1bee753b816b717e2fc8094",
    "libs.tech/magic/ihp-sg13cmos5l-drc.tech": "c220917168371ea6bfc572164e840095ae82db336add21c2e69d8691f8d159e4",
    "libs.tech/klayout/tech/drc/rule_decks/sg13cmos5l_tech_default.json": "3ff702c5bde8d01d027f30cdc6f5c08c0eff6b3e8fd7e709a6f40dcc73b1ca83",
    "libs.tech/klayout/tech/drc/rule_decks/feol/5_14_cont.drc": "a7d9bdd00aa46e44bb4e38d45afa8afa5ec2ad94c10638881d41cfe36d04b506",
}
ALIGNED_SHA256 = {
    "ihp-sg13cmos5l-cifin.tech": "57c9061f41b3a3bb77039233f7349f9866f4fabfcdbf2a8efdb26d7738a696bb",
    "ihp-sg13cmos5l-drc.tech": "b45438706028a7a8a85374a672cb78fdc49dd4897c12735fb88bd637bde072ec",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def align(source_tech, output):
    source_tech, output = source_tech.resolve(), output.resolve()
    source = source_tech.parent
    pdk = source.parents[1]
    require(source_tech.name == "ihp-sg13cmos5l.tech", "wrong technology")
    require(output.is_relative_to(Path.cwd().resolve()) and not output.exists(),
            "a new output below the working directory is required")
    for name, expected in REFERENCE_SHA256.items():
        require(digest(pdk / name) == expected, "pinned contact-rule input changed: " + name)
    originals = {p.relative_to(source).as_posix(): digest(p) for p in source.rglob("*") if p.is_file()}
    shutil.copytree(source, output)

    rules = output / "ihp-sg13cmos5l-drc.tech"
    text = rules.read_bytes().decode()
    start = text.index(" exemption SRAMID\n surround ndc/a")
    end = text.index(" exception none", start)
    block = text[start:end]
    require(block.count("70 absence_illegal") == 3 and block.count("20 absence_illegal") == 3
            and block.count("70 directional") == 3, "unexpected original contact-rule block")
    digital = ''' exception CONTACTDIGITAL
 surround ndc/a *ndiff,nfet 50 absence_illegal \\
    "N-diffusion overlap of contact in DigiBnd < %d (Cnt.c DigiBnd)"
 surround pdc/a *pdiff,pfet 50 absence_illegal \\
    "P-diffusion overlap of contact in DigiBnd < %d (Cnt.c DigiBnd)"
 surround nsc/a *nsd,*ntap 50 absence_illegal \\
    "N-tap overlap of contact in DigiBnd < %d (Cnt.c DigiBnd)"
'''
    changed = block.replace("exemption SRAMID", "exemption CONTACTSPECIAL", 1)
    changed = changed.replace(" exception SRAMID", digital + " exception SRAMID", 1)
    changed = changed.replace("20 absence_illegal", "6 absence_illegal")
    rules.write_bytes((text[:start] + changed + text[end:]).encode())

    cifin = output / "ihp-sg13cmos5l-cifin.tech"
    text = cifin.read_bytes().decode()
    anchor = " templayer sramarea SRAMID\n mask-hints SRAMID\n"
    require(text.count(anchor) == 1, "unexpected original SRAM marker derivation")
    added = '''
  # Cnt.c regions derived from actual GDS marker geometry.
  templayer contactspecial DIGITALID
  or SRAMID
  mask-hints CONTACTSPECIAL
  templayer contactdigital DIGITALID
  and-not SRAMID
  mask-hints CONTACTDIGITAL
'''
    cifin.write_bytes(text.replace(anchor, anchor + added).encode())
    staged = {name: digest(output / name) for name in originals}
    changed_files = {name: value for name, value in staged.items() if value != originals[name]}
    require(changed_files == ALIGNED_SHA256, "alignment differs from the tested two-file patch")
    require(all(digest(source / name) == expected for name, expected in originals.items()),
            "original PDK changed during staging")
    record = {
        "status": "STAGED_EXACT_CONTACT_RULE_ALIGNMENT", "source_technology": str(source_tech),
        "references": REFERENCE_SHA256, "original_files": originals, "staged_files": staged,
        "changed_files": changed_files,
        "contact_enclosure_nm": {"general": 70, "digital_outside_sram": 50, "sram_rule": 6,
                                 "sram_on_5nm_grid": 10, "sram_directional_unchanged": 70},
        "scope": "Only the three original low-voltage contact types. Markers are derived from actual GDS. No geometry edit, cell exclusion, report filter or waived rule. All other rules remain unchanged.",
    }
    (output / "alignment.json").write_bytes((json.dumps(record, indent=2) + "\n").encode())
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-tech", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(align(args.source_tech, args.output)["status"])


if __name__ == "__main__":
    main()
