#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Run inside the pinned workbench. The archive is MicroPython's upstream v1.29.0 source.
set -eu
archive=$(realpath "$1")
out=$(realpath -m "$2")
test ! -e "$out"
mkdir "$out"
printf '%s  %s\n' 8072f6ad42c0e3bbfca88ed09bf8f1106ce207a39129af920f70081b8f2fe286 "$archive" | sha256sum -c -
src=$(mktemp -d)
tar -xf "$archive" -C "$src"
tree="$src/micropython-1.29.0"
make -C "$tree/mpy-cross" -j2 > "$out/build.log" 2>&1
cross="$tree/mpy-cross/build/mpy-cross"
"$cross" --version > "$out/version.txt"
for mode in external parasite absent stuck; do
    python3 -B experiments/local_breakout/prepare.py "$mode" "$out/$mode"
    "$cross" -march=armv6m -s pico_job.py -o "$out/$mode/pico_job.mpy" "$out/$mode/pico_job.py"
done
python3 -B experiments/local_breakout/check_pio.py "$tree" "$out"
