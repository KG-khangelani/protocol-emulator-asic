# D36 - Freeze I2C pin acceptance before measuring instruction changes

Date: 2026-11-12. Goal: G2. Status: accepted for the next experiment.

## Decision

Use the [I2C contract](../specs/p-i2c-controller-100k.md) and independent public
event oracle before modifying the ISA. Start from D35's compact10 candidate.
First measure actual public-loaded SET/WAIT/WAIT_PIN programs and the complete
transaction footprint. A capacity or cleanup failure is useful evidence for a
general instruction/storage decision, not permission to add an I2C engine.

The bounded workload is ordinary seven-bit one-byte write/read and combined
write/repeated-START/read. It includes ACK/NACK, genuine open drain, stretch
handling, final-observation-edge priority and a 1 ms per-release timeout with
16-clock release/HALT cleanup. Firmware uses existing GPIO for distinct
OK/NACK/TIMEOUT markers; only the complete trace and terminal HALT authorize
accepting read data. Existing raw-valid alone is insufficient.

## Evidence and falsification

E0032 passes 19 oracle test groups with 3,902 recorded observations: 3,650 OK,
six NACK, 152 timeout fixtures, 18 explicit aborts and 76 rejected observations.
Repeated assessments and malformed traces are observations, not 3,902 distinct
hardware transactions. The main sweep includes every byte for all three
transaction kinds, all ordinary addresses, four input phases, every release
with stretching and both sides of the synchronized observation deadline.
Fifty-three full reference/counterexample witnesses are retained.

A direction mutation preserves every resolved wire value but transfers clock
generation to the target. The checker without SCL ownership/release-count
guards falsely accepts it; the completed oracle rejects it. The retained
development record also includes an initial test-edit NameError and correction.
The final suite passes. These are oracle failures/controls, not chip failures.

The timing review adds Table 11's data/ACK-valid maximum during unstretched low
phases, alongside minima and the 100 kHz ceiling. Simultaneous SDA/SCL changes
fail the project digital ordering margin. Neither rule establishes electrical
pad compliance. Reset, disable and loader entry have separately checked abort
effects and never count as accepted transfers.

## Limits and next action

No RTL, physical configuration or existing qualified evidence changes. G1's
compact10 qualification, P rejection, historical 6x4 results and pending owner
fluency remain intact. There is no I2C DUT, new formal, combined-protocol or
fresh physical pass yet. The oracle depends on a complete public event trace;
later adapters must check loading, initialization, isolation and input flush.

Next: test fitting public-loaded open-drain/wait kernels and a complete
existing-instruction transaction schedule. Record word count, cycles, real
loader rejection, input latency and cleanup failures before choosing changes.
Then satisfy the remaining G2 combined and physical gates on one candidate.

Evidence: [E0032](../../evidence/E0032-i2c-oracle/README.md).
