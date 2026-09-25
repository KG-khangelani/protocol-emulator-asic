# Fluency checkpoints

These are learning gates, not exams. A gap means we need another explanation or
experiment before relying on the concept in a design decision.

| Milestone | Technical gate | Fluency gate | State |
|---|---|---|---|
| M0 — Toolchain | GPIO baseline passes the qualified physical flow twice | Trace RTL to GDS; distinguish simulation, synthesis, timing, precheck and gate-level evidence | In progress |
| M1 — Sequencer | SET/WAIT/HALT semantics, tests and formal properties pass | Predict state-machine timing and interpret a counterexample | Not started |
| M2 — UART | Independent TX/RX waveform tests pass | Explain baud timing, asynchronous sampling and phase error | Not started |
| M3 — SPI/I2C | Shared core passes direction, stretching and contention cases | Explain clock modes, open-drain signalling and synchronizer latency | Not started |
| M4 — Compiler | Temporal IR lowers deterministically with diagnostics | Explain the software/hardware timing contract | Not started |
| M5 — Release | Reproducible submission candidate passes release gates | Independently run, inspect and defend the evidence bundle | Not started |

## M0 teach-back prompts

- Point to the line of RTL that creates clocked state.
- Explain reset priority using the waveform and specification table.
- Name one behaviour covered by the cocotb oracle and one behaviour it cannot
  establish.
- Explain why a positive setup slack is meaningful only with its clock target,
  timing corner and physical netlist.
- Explain why a GDS file can exist even when gate-level simulation fails.
- Identify the exact source commit and tool versions behind a physical result.
