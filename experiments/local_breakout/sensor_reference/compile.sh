#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Build the compiler from the checked MicroPython v1.29.0 source and compile the original Pico entry point.
set -eu
archive=$(realpath "$1")
out=$(realpath -m "$2")
test ! -e "$out"
mkdir "$out"
printf '%s  %s\n' 8072f6ad42c0e3bbfca88ed09bf8f1106ce207a39129af920f70081b8f2fe286 "$archive" | sha256sum -c -
tree=$(mktemp -d)
tar -xf "$archive" -C "$tree"
src="$tree/micropython-1.29.0"
make -C "$src/mpy-cross" -j2 > "$out/build.log" 2>&1
cross="$src/mpy-cross/build/mpy-cross"
"$cross" --version > "$out/version.txt"
"$cross" -march=armv6m -s pico.py -o "$out/pico.mpy" experiments/local_breakout/sensor_reference/pico.py
python3 - "$src" <<'PY'
import ast
from pathlib import Path
import sys
import types

src = Path(sys.argv[1])
assembler = src / "ports/rp2/modules/rp2.py"
native = types.ModuleType("_rp2")
native.PIO = types.SimpleNamespace(JOIN_NONE=0, SHIFT_LEFT=0, SHIFT_RIGHT=1)
sys.modules["_rp2"] = native
micro = types.ModuleType("micropython")
micro.const = lambda value: value
sys.modules["micropython"] = micro
rp2 = types.ModuleType("rp2")
exec(compile(assembler.read_bytes(), str(assembler), "exec"), rp2.__dict__)
path = Path("experiments/local_breakout/sensor_reference/pico.py")
tree = ast.parse(path.read_bytes())
tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "sample_dq"]
scope = {"rp2": rp2}
exec(compile(tree, str(path), "exec"), scope)
program = scope["sample_dq"]
assert list(program[0]) == [0x4001] and program[5] == ((1 << 18) | (1 << 16))
print("PASS: stock RP2040 ARMv6-M compilation and one pin per PIO cycle with right-shift autopush")
PY
