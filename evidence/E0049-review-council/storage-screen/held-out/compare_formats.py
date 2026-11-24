# SPDX-License-Identifier: Apache-2.0
"""Apply the same static literal-and-fixed-index codec to both power-query witnesses."""
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble


def size(values, literal_bytes, preload_bytes):
    count = len(values)
    distinct = len(set(values))
    width = (distinct - 1).bit_length()
    indices = (count * width + 7) // 8
    dense = 4 + literal_bytes*distinct + indices
    return {"instruction_words": count, "unique": distinct, "literal_bytes": literal_bytes, "width": width,
            "raw_program_bytes": literal_bytes*count, "header_bytes": 4, "dictionary_bytes": literal_bytes*distinct,
            "index_bytes": indices, "dense_bytes": dense, "dense_whole_block_4byte_aligned": (dense + 3)//4*4,
            "raw_fallback_with_4byte_header": 4 + literal_bytes*count, "external_preload_bytes": preload_bytes,
            "binary_sha256_le": hashlib.sha256(b"".join(v.to_bytes(literal_bytes, "little") for v in values)).hexdigest()}


if __name__ == "__main__":
    vm_source = ROOT / "evidence/E0049-review-council/onewire/power_query.asm"
    pio_hex = ROOT / "evidence/E0049-review-council/panel-a/pio/normal.hex"
    vm = [int(v, 16) for v in assemble(vm_source.read_text("utf-8"))["words"]]
    pio = [int(v, 16) for v in pio_hex.read_text("ascii").splitlines()]
    print(json.dumps({"vm_power_query": size(vm, 4, 0), "pio_power_query": size(pio, 2, 4)}, indent=2))
