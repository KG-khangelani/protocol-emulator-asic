# Milestones and deadline

Hard deadline: **18 January 2027**. These are evidence gates; internal dates
below are planning targets, not externally imposed deadlines or forecasts.

| Gate | Outcome | Required evidence | Planning target |
|---|---|---|---|
| M0 | Reliable toolchain | GPIO RTL through GDS; reports and clean rerun | 4 Oct 2026 |
| M1 | Deterministic sequencer | Spec, reference model, timing tests and formal properties | 25 Oct |
| M2 | UART in firmware | Differential TX/RX waveforms and resource measurements | 15 Nov |
| M3 | Shared UART/SPI/I2C core | Same datapath and ISA; protocol/timing/error coverage | 6 Dec |
| M4 | Compiler and tooling | Reproducible temporal IR lowering and diagnostics | 20 Dec |
| M5 | Submission candidate | Physical fit, verification, FPGA where available and release package | 10 Jan 2027 |
| Submission | Final public source and evidence | Submission requirements rechecked; receipt recorded | Before 18 Jan |

If a gate slips, reduce optional architecture/tooling and stretch scope first.
Avoid sacrificing reproducibility and timing verification to add protocols.
The interval after 10 January is reserved for integration and submission repair.
