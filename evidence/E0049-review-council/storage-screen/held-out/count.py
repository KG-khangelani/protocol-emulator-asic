# SPDX-License-Identifier: Apache-2.0
"""Count two held-out full-word dictionaries and compare to the original public loader."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT))
from tools.assembler import assemble, load_plan


def sizes(words):
    length = len(words)
    unique = len(set(words))
    width = (unique - 1).bit_length()
    header = 4
    dictionary = 4 * unique
    index_bytes = (length * width + 7) // 8
    index_words = (length + (32 // width) - 1) // (32 // width) if width else 0
    return {"instructions": length, "unique_words": unique, "index_width_bits": width, "expanded_bytes": 4*length,
            "header_bytes": header, "dictionary_bytes": dictionary, "byte_packed_indices": index_bytes,
            "dense_bytes": header + dictionary + index_bytes, "dense_32b_row_crossings": sum(
            (i * width) % 32 + width > 32 for i in range(length)),
            "non_straddling_32b_rows": index_words, "whole_row_non_straddling_bytes": header + dictionary + 4*index_words}


def main():
    paths = [("evidence/E0049-review-council/onewire/power_query.asm", 85),
             ("evidence/E0049-review-council/panel-c/spi-target/spi_test_target.asm", 59)]
    result = {}
    for name, expected_length in paths:
        source = (ROOT / name).read_bytes()
        program = assemble(source.decode("utf-8"))
        words = [int(code, 16) for code in program["words"]]
        if len(words) != expected_length:
            raise ValueError(f"{name} count changed")
        steps = load_plan(program)["steps"]
        result[name] = {"source_sha256": hashlib.sha256(source).hexdigest(),
                        "image_sha256": hashlib.sha256(b"".join(word.to_bytes(4, "little") for word in words)).hexdigest(),
                        **sizes(words), "current_loader_steps": len(steps),
                        "current_loader_action_counts": dict(sorted(Counter(step["action"] for step in steps).items()))}
    # Only the value diversity matters to this counting example. This is not a program execution.
    result["128_distinct_values"] = sizes(range(128))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
