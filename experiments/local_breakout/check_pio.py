# SPDX-License-Identifier: Apache-2.0
"""Assemble the exact PIO functions with upstream rp2.py and verify their instruction words."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import types


def check(tree, out):
    # Only these native constants are needed by the upstream pure-Python PIO assembler.
    native = types.ModuleType("_rp2")
    native.PIO = types.SimpleNamespace(JOIN_NONE=0, SHIFT_LEFT=0, SHIFT_RIGHT=1, OUT_LOW=2)
    sys.modules["_rp2"] = native
    micro = types.ModuleType("micropython")
    micro.const = lambda x: x
    sys.modules["micropython"] = micro
    asm_path = tree/"ports/rp2/modules/rp2.py"
    rp2 = types.ModuleType("rp2")
    exec(compile(asm_path.read_bytes(), str(asm_path), "exec"), rp2.__dict__)
    jobs = {}
    expected = {"project_clock": [0xe401, 0xe400], "sample_pins": [0x4010]}
    for mode in ("external", "parasite", "absent", "stuck"):
        source = (out/mode/"pico_job.py").read_bytes()
        parsed = ast.parse(source)
        parsed.body = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in expected]
        namespace = {"rp2": rp2}
        exec(compile(parsed, "pico_job.py", "exec"), namespace)
        words = {name: list(namespace[name][0]) for name in expected}
        if words != expected or namespace["sample_pins"][5] != ((1 << 18) | (1 << 16)):
            raise ValueError("PIO clock or right-shifted 32-bit autopush")
        jobs[mode] = dict(source_sha256=hashlib.sha256(source).hexdigest(),
                          mpy_sha256=hashlib.sha256((out/mode/"pico_job.mpy").read_bytes()).hexdigest())
    receipt = dict(compiler=(out/"version.txt").read_text().strip(), pio_words=words, jobs=jobs,
                   assembler_sha256=hashlib.sha256(asm_path.read_bytes()).hexdigest())
    (out/"result.json").write_text(json.dumps(receipt, indent=2)+"\n")
    print(receipt["compiler"], "four modes compiled and PIO words checked")


if __name__ == "__main__":
    check(Path(sys.argv[1]), Path(sys.argv[2]))
