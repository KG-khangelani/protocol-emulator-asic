# D15: Compose an eight-bit transfer from one-bit shift steps

Date: 2026-10-05. Status: accepted for the K-SHIFT-8 candidate.

## Decision

Add a protocol-independent `SHIFT_STEP` operation rather than a monolithic
eight-bit transfer. The existing bounded LOOP executes it exactly eight times.
The loader gains an eight-bit TX payload register and read-only RX result/valid
registers, while the engine owns only in-progress shift state.

## Rationale

- The bounded loop already supplies iteration count and termination, so another
  hidden byte counter would duplicate qualified machinery.
- One-bit retirement gives SET and WAIT explicit places between bits for later
  clock, framing, and rate schedules instead of embedding a protocol phase
  machine in RTL.
- Separate public payload/result registers let the same program process new
  data without encoding payload bytes as instructions and make receive evidence
  observable after the engine is reset into loader mode.
- Latching bit order and pin selection at the first step, then faulting on a
  mid-byte change, keeps every partial transfer deterministic and fail closed.
- The eighth-step completion condition feeds the RX store directly; a measured
  first implementation's registered handoff was rejected because it added nine
  state bits and one hidden commit edge without changing observable capability.

## Consequences

The first kernel consumes three of eight program words and ten accepted engine
edges. Input stimulus must account for the already adopted two-stage
synchronizer. The operation is a reusable serial datapath primitive, not an SPI
clock generator or UART implementation. Its complete-chip state and generic
synthesis cost must be measured before it is retained in a final ISA.
