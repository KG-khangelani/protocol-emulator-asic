# SPDX-License-Identifier: Apache-2.0
"""Reproduce the D38 byte-write rewrite from immutable E0035 source inputs."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "evidence/E0035-general-i2c/sources/current"
EVIDENCE = ROOT / "evidence/E0037-explicit-store-lanes"
MANIFEST = EVIDENCE / "sources/source-manifest.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def generate():
    original = json.loads((BASE / "source-manifest.json").read_bytes())["od128"]
    sources = {name: (BASE / "od128" / name).read_bytes() for name in original["source_sha256"]}
    if {name: digest(raw) for name, raw in sources.items()} != original["source_sha256"]:
        raise ValueError("frozen E0035 source changed")

    def replace(match):
        indent, choice, index = match.groups()
        body = "\n".join(f"{indent}        2'd{lane}: word{index}[{8*lane+7}:{8*lane}] <= data_in;" for lane in range(4))
        return f"{indent}{choice}: begin\n{indent}    case (byte_address[1:0])\n{body}\n{indent}    endcase\n{indent}end"

    text, count = re.subn(r"(?m)^( +)(\d+'d\d+): word(\d+)\[8\*byte_address\[1:0\] \+: 8\] <= data_in;",
                          replace, sources["m1_program_store.v"].decode())
    if count != 128:
        raise ValueError("the rewrite must cover exactly 128 real words")
    sources["m1_program_store.v"] = text.encode()
    screened = json.loads((ROOT / "evidence/E0036-g2-store-and-ci/lane-screen/generic/result.json").read_bytes())
    hashes = {name: digest(raw) for name, raw in sources.items()}
    if hashes != screened["measurements"]["od128"]["source_sha256"]:
        raise ValueError("generated chip differs from the measured/equivalent lane screen")
    return sources, {"od128": dict(original, source_sha256=hashes, implementation="od128-lanes",
                                   parent_source_sha256=original["source_sha256"])}


def build(output):
    if output.exists() or not output.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("new isolated build output required")
    sources, manifest = generate()
    if manifest != json.loads(MANIFEST.read_bytes()):
        raise ValueError("generated candidate differs from the frozen D38 manifest")
    target = output / "od128/src"
    target.mkdir(parents=True)
    for name, raw in sources.items():
        (target / name).write_bytes(raw)
    (output / "source-manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    return manifest
