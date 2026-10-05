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
- [x] Provide and remotely qualify a beginner-readable M0 waveform walkthrough (E0012).
- [x] Expose and remotely qualify conservative fluency status without automatic promotion (E0013).
- [x] Qualify Node 24 Docker CI actions and remove the Node 20 runtime warning (E0011).
- [x] Qualify Docker-independent `LearnStatus` and `LearnM0 RTL` on clean Windows CI (E0014).
- [x] Qualify the complete locked local ladder with Docker Desktop opened (E0015).
- [ ] Complete and record the M0 owner fluency teach-back.

Reference: `docs/specs/m0-gpio.md`; evidence index: `evidence/README.md`.
Do not substitute a static syntax check or generic synthesis for physical fit.

## R0-T01 — Pre-M1 architecture research (active supporting work)

Outcome: compare credible programmable substrates with one evidence contract,
without choosing an ISA by reputation or importing unverified external claims.

- [x] Map fixed RTL, PIO-style, temporal-sequencer and tiny-CPU families.
- [x] Lock exact established and contemporary source identities.
- [x] Separate upstream self-reports from project measurements.
- [x] Define shared workloads, accounting boundaries, metrics and statuses.
- [x] Define falsification gates and the decision process for M1 experiments.

References: `research/architecture-landscape.md` and
`research/evaluation-contract.md`. This research is complete. D8 now allows
engineering to proceed independently while M0 owner fluency remains pending.

## Follow-on tasks

| ID | Work | Exit gate | State |
|---|---|---|---|
| M1-T01 | Define execution, PC, reset, I/O, WAIT and HALT semantics | Reviewable cycle tables and invalid-program behavior | Implemented candidate in `specs/m1-execution-contract.md`; encoding remains provisional |
| M1-T02 | Implement SET/WAIT/HALT and independent reference model | Exact timing regression plus reset/PC/wait properties | Implemented candidate; local dual-simulator/formal/generic synthesis pass |
| M1-T04 | Public-pin program load and readback | Program A/reset/program B public-pin trace; invalid image fail-closed | Qualified at `d502227`: exact-head CI passes P-RELOAD simulation and store proof |
| M1-T05 | Synchronize inputs and add bounded event wait | Two-stage latency, final-edge event priority, timeout and enable freeze checked | Qualified at `14a93b4`: exact-head dual-simulator/formal/generic synthesis CI pass |
| M1-T06 | Execute K-INPUT-WAIT as a public-pin-loaded kernel | Same image takes event/timeout paths and HALTs within declared bounds against independent traces | Qualified at `f383744`: exact-head CI passes complete locked ladder |
| M1-T07 | Execute K-BOUNDED-LOOP as a public-pin-loaded kernel | Counts 0, 1, 2 and 255 produce exact bounded traces and HALT | Qualified by exact-head CI and independent review; PR 2 merged at `b3b73e6` |
| M1-T08 | Preserve simulation waveform provenance | Full RTL and GL-shaped smoke FST/JUnit pairs retain distinct paths, stage labels and verified checksums | Qualified by exact-head CI and independent review; PR 3 merged at `2326022` |
| M1-T09 | Execute K-SHIFT-8 as a public-pin-loaded kernel | Both bit orders, exact ten-edge bound, RX readback, data-register and partial/error behavior match independent expectations | Qualified at `d1ddc8a`; exact-head CI/re-review passed and PR 4 merged at `081a8b1` |
| M1-T03 | Add GET and BRANCH only as needed; bounded LOOP was evaluated by M1-T07 | Bounded behavior; cost delta recorded | Queued |
| M2-T01 | UART waveform oracle and VM transmit/receive | Randomized payloads, framing/error cases and timing checks | TX PR5 merged at `80975ed` (E0016); RX semantic PR6 merged at `3797c5a` (E0017); bounded last-byte PR7 merged at `155e130` (E0018); D19 host-serviced pair H+L<=10P and unsafe-overwrite counterexample pass focused/coherent local checks and re-review (E0019), clean CI pending; no RTL/storage delta; continuous/autonomous delivery open |
| M3-T01 | SPI and I2C on shared core | Direction, sampling, stretching and contention cases | Queued |
| M3-T02 | Compare architecture and instruction ablations | Program bytes, cycles, mapped area and verification cost | Queued |
| M4-T01 | Temporal IR and compiler | Deterministic output, diagnostics and timing checks | Queued |
| M5-T01 | Formal/random/FPGA/physical release validation | Reproducible submission evidence | Queued |

Do not preallocate a program-memory size or promise a protocol bitrate before
measurement establishes feasibility.
