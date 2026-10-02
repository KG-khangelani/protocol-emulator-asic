<!-- Modified 2026-10-02: M1 simulation-candidate datasheet. -->
## How it works

This is an M1 simulation candidate for the Protocol Emulator ASIC. A bounded
SET/WAIT/HALT engine executes a four-word internal preload. Active-low
synchronous reset clears PC, state, wait count, GPIO value and GPIO direction;
reset wins over enable. `uio_out/uio_oe` expose the logical GPIO bank and
`uo_out` exposes execution state and PC. Dedicated inputs are unused.

The preload is an experiment, not post-fabrication programmability. Public-pin
loading/readback, input synchronization and protocol firmware remain future work.

## How to test

Hold `rst_n` low through a rising edge, then deassert it before a later edge.
With `ena` high, the preload drives `A5`, waits two accepted edges, changes the
low GPIO nibble, and halts. With `ena` low, all architectural state holds. See
`docs/specs/m1-execution-contract.md` and run `make test`.

## External hardware

No external hardware result is claimed. The 50 MHz flow value remains a target;
this candidate has no new CMOS5L timing, fit, gate-level or silicon evidence.
