<!-- Modified 2026-10-02: M1 simulation-candidate datasheet. -->
## How it works

This is an M1 simulation candidate for the Protocol Emulator ASIC. A bounded
SET/WAIT/HALT/WAIT_PIN engine executes up to eight public-pin-loaded words. Active-low
synchronous reset clears PC, state, wait count, GPIO value and GPIO direction;
reset wins over enable. `uio_out/uio_oe` expose the logical GPIO bank and
`uo_out` exposes execution state and PC. Dedicated inputs are unused.

The synchronous loader supports byte writes, length commit, and readback.
Each `uio_in` bit has a two-stage clocked synchronizer. `WAIT_PIN` observes the
second stage and either faults or conditionally skips after its explicit
accepted-edge timeout. A three-word programmed kernel demonstrates bounded
event and timeout paths to HALT. This is an RTL latency contract, not analog
metastability evidence. Protocol firmware remains future work.

## How to test

Hold `rst_n` low through a rising edge, then deassert it before a later edge.
Use `ui_in[7:5]` for loader mode/write/length selection, `ui_in[4:0]`
for byte address, and `uio_in/out` for data. Commit length last, release loader
mode, and execution begins at word zero. See `docs/specs/m1-program-loader.md`.

## External hardware

No external hardware result is claimed. The 50 MHz flow value remains a target;
this candidate has no new CMOS5L timing, fit, gate-level or silicon evidence.
