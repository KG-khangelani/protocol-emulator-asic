# Progress report: M1 execution contract and implementation

Date: 2026-10-02. Scope: simulation-only specification work.

## Engineering completed autonomously

- Drafted exact SET, WAIT, HALT, reset/enable, PC, GPIO, HALT, and invalid-program
  semantics in `docs/specs/m1-execution-contract.md`.
- Reconciled the subset with the adopted evaluation contract: unsupported
  microkernels, reload, protocol workloads, complete-chip cost, and physical
  results remain `NOT_EVALUATED`.
- Added a reusable synthesizable engine, provisional preload, independent Python
  semantic model, pin-level Icarus/Verilator comparison, formal properties and
  a falsification check. These are pre-physical engineering results.
- Rechecked the official competition page on 2026-10-02: January 18, 2027
  submission deadline, IHP 130 nm CMOS5L, 6x4 maximum allocation, and a
  reprogrammable general-purpose protocol emulator remain the pertinent bounds.

## Learning gate and decisions reserved

M0 technical evidence remains closed, and the owner-fluency checkpoint remains
`PENDING`. By explicit owner approval, engineering now progresses independently;
no learning status was promoted. The provisional encoding and preload implement
the reviewed subset but do not provide post-fabrication loading.

Remaining engineering work includes public-pin loader/readback, program storage
selection, input synchronization, bounded event waits, protocol workloads and
new CMOS5L qualification. Owner teach-back remains a separate next learning
action when capacity permits.
