# Progress report: proposed M1 execution contract

Date: 2026-10-02. Scope: simulation-only specification work.

## Engineering completed autonomously

- Drafted exact SET, WAIT, HALT, reset/enable, PC, GPIO, HALT, and invalid-program
  semantics in `docs/specs/m1-execution-contract.md`.
- Reconciled the subset with the adopted evaluation contract: unsupported
  microkernels, reload, protocol workloads, complete-chip cost, and physical
  results remain `NOT_EVALUATED`.
- Added a deliberately isolated Python semantic model and unit checks. They are
  specification-level executable examples, not production VM RTL or hardware
  evidence.
- Rechecked the official competition page on 2026-10-02: January 18, 2027
  submission deadline, IHP 130 nm CMOS5L, 6x4 maximum allocation, and a
  reprogrammable general-purpose protocol emulator remain the pertinent bounds.

## Learning gate and decisions reserved

M0 technical evidence remains closed, but the owner-fluency checkpoint remains
`PENDING`. This work does not change the active milestone, advance learning
status, implement a VM, select an encoding or memory capacity, rerun physical
closure, purchase hardware, or submit to the competition.

Before production RTL, review is required for the abstract GPIO-to-public-pin
mapping, instruction encoding, representable WAIT maximum, program storage and
fetch latency, and loader/readback contract. The next project gate remains the
owner M0 teach-back; after that, this proposal can be accepted or revised as the
input to M1 implementation.

