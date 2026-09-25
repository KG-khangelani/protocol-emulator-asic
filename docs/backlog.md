# Executable backlog

## M0-T01 — Establish RTL-to-GDS baseline (active)

Outcome: a reproducible, deterministic GPIO design hardened with the official
IHP CMOS5L Tiny Tapeout flow.

- [x] Import and identify the official template.
- [x] Set the documented 6x4 competition allocation.
- [x] Specify waveform, reset, enable and unused-pin behavior.
- [x] Implement baseline RTL and independent pin-level regression.
- [x] Prepare Codex instructions, CI and evidence collection.
- [x] Pass the audited public-release gate and enable repository security controls.
- [x] Build and validate the locked local doctor/lint/test/synthesis workbench.
- [x] Pass the full locked ladder from a fresh Windows clone without native EDA (E0009).
- [x] Run static repository checks.
- [x] Create GitHub remote.
- [x] Populate remote and pass CI (E0002).
- [x] Pass cycle-level simulation; FST/JUnit uploaded to CI artifact (E0002).
- [x] Archive CI artifact durably before 21 December 2026 (E0002).
- [x] Pass generic synthesis sanity check (E0002).
- [x] Complete official CMOS5L RTL-to-GDS build and precheck (E0003).
- [x] Pass and archive the corrected official GDS, gate-level, and precheck run (E0006).
- [x] Add Verilator as a second simulator in the locked workbench.
- [x] Prove the M0 reset/count/wrap/hold/output/input-independence contract locally.
- [x] Pass and archive remote fast CI with Icarus, Verilator, formal, and synthesis (E0007).
- [x] Record mapped area, post-route timing/slack, violations, utilization and GDS hash (E0003).
- [x] Record resolved action/tool/PDK versions and environment (E0003).
- [x] Pin direct workflow actions and the qualified physical-flow inputs.
- [x] Add and remotely validate the non-gating upstream drift canary (E0008).
- [x] Clean repository-pinned rerun reproduces the functional and physical result (E0010).
- [x] Provide a runnable, source-backed M0 evidence walkthrough.
- [ ] Complete and record the M0 owner fluency teach-back.

Reference: `specs/m0-gpio.md`; evidence index: `../evidence/README.md`.
Do not substitute a static syntax check or generic synthesis for physical fit.

## Follow-on tasks

| ID | Work | Exit gate | State |
|---|---|---|---|
| M1-T01 | Define execution, PC, reset, I/O, WAIT and HALT semantics | Reviewable cycle tables and invalid-program behavior | Queued |
| M1-T02 | Implement SET/WAIT/HALT and independent reference model | Exact timing regression plus reset/PC/wait properties | Queued |
| M1-T03 | Add GET, BRANCH and bounded LOOP only as needed | Bounded behavior; cost delta recorded | Queued |
| M2-T01 | UART waveform oracle and VM transmit/receive | Randomized payloads, framing/error cases and timing checks | Queued |
| M3-T01 | SPI and I2C on shared core | Direction, sampling, stretching and contention cases | Queued |
| M3-T02 | Compare architecture and instruction ablations | Program bytes, cycles, mapped area and verification cost | Queued |
| M4-T01 | Temporal IR and compiler | Deterministic output, diagnostics and timing checks | Queued |
| M5-T01 | Formal/random/FPGA/physical release validation | Reproducible submission evidence | Queued |

Do not preallocate a program-memory size or promise a protocol bitrate before
measurement establishes feasibility.
