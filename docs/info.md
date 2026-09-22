<!-- Modified 2026-09-22: M0 project datasheet. -->
## How it works

This is the M0 toolchain baseline for Protocol Emulator ASIC. An 8-bit counter
increments on each rising clock edge when `ena` is high. Active-low synchronous
reset clears it; reset wins over enable. The counter wraps from 255 to 0.
Dedicated output `uo[i]` shows counter bit `i`. All bidirectional pins remain
inputs, and their output paths are tied low. Dedicated inputs are unused.
The baseline is not yet a programmable protocol emulator.

## How to test

Hold `rst_n` low through a rising edge, then deassert it before a later edge.
With `ena` high, observe outputs 1, 2, 3, ... 255, 0. With `ena` low, outputs
hold their previous value. See `specs/m0-gpio.md` for exact cycle semantics and
run `make test` from the repository root for the pin-level regression.

## External hardware

A clock/reset source and logic analyzer can observe the waveform. The initial
flow target is 50 MHz; no fabricated device or timing closure is claimed yet.
