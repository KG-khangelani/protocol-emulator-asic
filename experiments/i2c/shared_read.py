# SPDX-License-Identifier: Apache-2.0
"""Reproduce D39's shared word read from the immutable D38 complete chip."""
import json
import re

from store_lanes import EVIDENCE as PARENT, ROOT, digest

EVIDENCE = ROOT / "evidence/E0038-shared-program-read"
MANIFEST = EVIDENCE / "sources/source-manifest.json"
SCREEN = PARENT / "shared-read-screen"


def generate():
    parent = json.loads((PARENT / "sources/source-manifest.json").read_bytes())["od128"]
    sources = {name: (PARENT / "sources/od128" / name).read_bytes() for name in parent["source_sha256"]}
    if {name: digest(raw) for name, raw in sources.items()} != parent["source_sha256"]:
        raise ValueError("immutable D38 source changed")
    original = sources["m1_program_store.v"].decode()
    if original.count("    always @(*) begin") != 1:
        raise ValueError("expected one combinational read block")
    first = original.index("    always @(*) begin")
    last = original.index("    assign instruction_valid")
    block = original[first:last]
    fetch = re.findall(r"(?ms)^        case \(pc\).*?^        endcase$", block)
    if len(fetch) != 1 or fetch[0].count(": instruction = word") != 128:
        raise ValueError("expected all 128 real fetch words")
    if "if (load_length)\n            data_out = program_length;" not in block:
        raise ValueError("length readback override missing")
    replacement = "    wire [7:0] read_address = load_mode ? {1'b0, bank_address[8:2]} : pc;\n"
    replacement += "    always @(*) begin\n" + fetch[0].replace("case (pc)", "case (read_address)")
    replacement += "\n        data_out = instruction[8*byte_address[1:0] +: 8];\n"
    replacement += "        if (load_length)\n            data_out = program_length;\n    end\n"
    sources["m1_program_store.v"] = (original[:first] + replacement + original[last:]).encode()
    hashes = {name: digest(raw) for name, raw in sources.items()}
    screen = json.loads((SCREEN / "verification.json").read_bytes())
    proof = json.loads((SCREEN / "chip-equivalence/verification.json").read_bytes())
    if hashes != screen["sources"] or hashes != proof["sources"]["gate"]:
        raise ValueError("generated source differs from the measured and proved shared read")
    return sources, {"od128": dict(parent, source_sha256=hashes, implementation="od128-shared",
                                   parent_source_sha256=parent["source_sha256"])}


def build(output):
    if output.exists() or not output.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated build output required")
    sources, manifest = generate()
    if manifest != json.loads(MANIFEST.read_bytes()):
        raise ValueError("generated candidate differs from the frozen D39 manifest")
    target = output / "od128/src"
    target.mkdir(parents=True)
    for name, raw in sources.items():
        (target / name).write_bytes(raw)
    (output / "source-manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    return manifest
