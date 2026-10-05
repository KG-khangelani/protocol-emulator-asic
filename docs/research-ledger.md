# Research ledger

Question: **What is the smallest computational substrate that can efficiently
express useful digital communication protocols under hard temporal constraints?**

## Verified facts

| ID | Fact | Evidence |
|---|---|---|
| F1 | Competition requires an open-source reprogrammable protocol emulator, deadline 18 Jan 2027 | S1, `sources.md` |
| F2 | Current allocation is 6x4; 8x4 is only a possibility in the brief | S1 |
| F3 | CMOS5L source snapshot was imported with matching blob identities | `upstream-template.json`, initial Git commit |
| F4 | M0 can be placed and routed in the 6x4 CMOS5L allocation with positive reported slack at the 20 ns flow target and clean recorded physical checks | E0003, E0006, E0010 |
| F5 | The first official gate-level job cannot elaborate because its source list omits the PDK file defining `ihp_dff_r` | E0003 |
| F6 | The locked Linux/amd64 workbench passes exact-version checks, Verible lint, two M0 RTL tests and generic synthesis on Windows Docker Desktop | E0005 |
| F7 | The corrected official run passes GDS generation, both generated-netlist tests, and all nine Tiny Tapeout prechecks | E0006 |
| F8 | E0003 and E0006 have byte-identical GDS non-timestamp records; their full hashes differ only because 256 bytes in library/structure timestamp records changed | E0006 |
| F9 | The M0 public-pin transition/output assertions pass k-induction, the reset-to-wrap covers are reachable, and the same assertions reject an increment-by-two mutant locally and in clean remote CI | E0007, `../formal/README.md` |
| F10 | The read-only upstream canary remotely observes the live Tiny Tapeout CMOS5L action ref without altering qualified pins; its baseline state was CURRENT | E0008 |
| F11 | A fresh Windows clone passes the full locked fast ladder without native EDA commands on PATH, and its compared physical-input byte hashes equal Linux CI | E0009 |
| F12 | The clean repository-pinned physical flow passes GDS, both gate-level tests and all nine prechecks; it reproduces E0006's metrics and every non-timestamp GDS record | E0010 |
| F13 | Immutable Node 24 Docker action releases preserve the complete locked fast-CI result and remove the prior Node 20 deprecation annotation | E0011 |
| F14 | A clean remote checkout runs the readable M0 waveform lab, checks all 1,561 rising edges against the declared transition table, and rejects an intentionally corrupted count edge | E0012 |
| F15 | Clean CI retains separate technical/fluency gate validation and rejects a deliberately unearned active-milestone fluency PASS | E0013 |
| F16 | A clean Windows checkout runs the read-only M0 status and RTL lessons through host Python without invoking Docker, while the complete locked Linux verification ladder remains green | E0014 |
| F17 | With Docker Desktop opened, the Windows host runs signed version 4.92.0 with a healthy Linux/amd64 engine and passes all nine locked local M0 evidence stages at a clean source revision | E0015 |

## Verified upstream observations (not project measurements)

| ID | Observation | Evidence and boundary |
|---|---|---|
| O1 | The pinned Raspberry Pi SDK describes an RP2040 PIO block as four independently programmable state machines with shift/scratch registers, a clock divider and FIFO access; its instruction header defines nine major operations | S9, `research/source-lock.json`; no IHP area or timing inference |
| O2 | SERV's pinned README describes a bit-serial RISC-V core and reports 2.1 kGE for a typical CMOS configuration | S10; upstream figure not reproduced and not technology-comparable here |
| O3 | PicoRV32's pinned README describes configurable RV32E/RV32I variants and approximately four CPI under stated memory assumptions | S11; upstream performance and FPGA figures not reproduced here |
| O4 | OpenTitan's pinned protocol-IP documentation covers fixed UART, SPI-host and I2C blocks, including I2C open-drain, synchronization, clock-stretching and timeout concerns | S12; feature reference, not a small-area baseline |
| O5 | Three pinned public competition READMEs independently describe deterministic programmable cores or sequencers | C1-C3; repository self-reports only, all implementation/result claims `NOT_EVALUATED` |

## Working hypotheses

| ID | Claim | Falsification gate | State |
|---|---|---|---|
| H1 | A temporal VM covers UART, SPI and I2C compactly | Requires protocol-specific RTL escape paths or misses timing/fit | Unproven |
| H2 | Explicit timing instructions simplify verification | A program plus timing table cannot predict every required edge/response, or hidden latency prevents bounded properties | Unproven |
| H3 | The candidate instruction set is near minimal | Removing/merging an instruction preserves coverage at acceptable cost | Unproven |
| H4 | Interpretation overhead fits useful bit timing | Measured execution/post-route timing misses required sample/edge windows | Unproven |

## Design decisions

| ID | Decision | Basis |
|---|---|---|
| D1 | Preserve official template; use an isolated GPIO M0 baseline | `decisions/0001-bootstrap.md` |
| D2 | Use 50 MHz as the initial test/flow target, not a supported-performance claim | Inherited 20 ns template constraint; reassess after hardening |
| D3 | Use a locked Docker workbench for the fast verification lane | `decisions/0003-locked-workbench.md` |
| D4 | Keep M0 physical acceptance on the official flow with direct actions and successful candidate inputs pinned immutably | `decisions/0004-pinned-physical-flow.md`, E0006, E0010 |
| D5 | Pin Node 24-native Docker CI orchestration releases and qualify them without changing the EDA image | `decisions/0005-node24-ci-actions.md`, E0011 |
| D6 | Compare CHIP_COMPLETE candidates with shared workloads, two-axis result labels and predeclared falsification/selection rules | `decisions/0006-architecture-evaluation-contract.md`, `research/evaluation-contract.md` |
| D7 | Keep evidence-reading lessons available through host Python while retaining Docker as the execution boundary for every EDA command | `decisions/0007-docker-independent-learning.md`, E0014 |
| D8 | Allow engineering progress independently while preserving conservative owner-fluency gates | `decisions/0008-decouple-engineering-learning.md` |
| D9 | Use a provisional 32-bit SET/WAIT/HALT encoding and simulation preload without claiming public-pin reload | `decisions/0009-m1-provisional-encoding.md` |
| D10 | Replace the constant preload with an eight-word clock-synchronous public-pin store and readback path | `decisions/0010-public-pin-program-store.md` |
| D11 | Synchronize public inputs and make every input wait terminate within an explicit accepted-edge bound | `decisions/0011-synchronized-bounded-input-wait.md` |
| D12 | Add one-bit WAIT_PIN timeout skip as the minimum conditional needed by K-INPUT-WAIT | `decisions/0012-k-input-wait-timeout-skip.md` |
| D13 | Evaluate an 8-bit non-nested bounded block before introducing shift-specific data state | `decisions/0013-bounded-block-before-shifter.md` |
| D14 | Preserve separate full-RTL and GL-shaped-smoke waveform identities and verify their stage labels and checksums | `decisions/0014-distinct-waveform-provenance.md` |
| D15 | Compose eight-bit transfers from one-bit SHIFT_STEP operations and existing bounded LOOP, with public TX/RX data registers | `decisions/0015-composable-shift-step.md` |
| D16 | Extend the reusable shifter with a timed byte burst and two alternating payload slots; keep UART framing in SET/WAIT firmware | `decisions/0016-timed-shift-burst.md` |
| D17 | Falsify an eight-word UART-RX sampling/check schedule before changing result delivery; keep raw capture distinct from frame acceptance | `decisions/0017-rx-contract-before-delivery-extension.md` |
| D18 | Deliver only the last byte of a validated two-frame batch and expose raw data through a generic dedicated-output runtime selector without GPIO contention or new state | `decisions/0018-bounded-rx-delivery-runtime-readout.md` |
| D19 | Quarantine raw byte one in an external synchronous host with H+L<=10P and accept both only after known-image HALT; do not add buffering for this bounded serviced batch | `decisions/0019-service-raw-bytes-before-buffering.md` |

## Experimental results

| ID | Experiment | Result | Limit |
|---|---|---|---|
| E0001 | Bootstrap consistency and tool availability | Static pass; HDL stages blocked | No behavioral or physical evidence; `../evidence/E0001-bootstrap/` |
| E0002 | GitHub CI baseline | Static, RTL and generic synthesis PASS; docs PASS | No physical/GL proof; `../evidence/E0002-ci/` |
| E0003 | First official CMOS5L run | GDS and all prechecks PASS; gate-level compile FAIL | Not a complete M0 result; no functional GL run or clean rerun; `../evidence/E0003-cmos5l-first-run/` |
| E0005 | Locked local open EDA workbench | Doctor, static, lint, 2 RTL tests and generic synthesis PASS | Formal and physical fit NOT_EVALUATED; `../evidence/E0005-locked-workbench/` |
| E0006 | Corrected official CMOS5L run | GDS, 2 gate-level tests, and all 9 prechecks PASS | Mutable workflow ref at dispatch; no clean repository-pinned rerun; `../evidence/E0006-cmos5l-corrected-run/` |
| E0007 | Locked fast CI and M0 formal proof | Static, lint, 2 Icarus tests, 2 Verilator tests, formal proof/covers/mutant, and generic synthesis PASS | Written-property coverage only; no physical or silicon proof; `../evidence/E0007-locked-fast-ci/` |
| E0008 | Upstream drift canary baseline | Remote monitor PASS; live and qualified Tiny Tapeout action commits match | Timestamped observation only; no automatic upgrade or physical proof; `../evidence/E0008-upstream-canary/` |
| E0009 | Fresh Windows clone verification | Doctor, static, lint, both simulators, formal, and generic synthesis PASS; cross-platform input hashes match | Reused qualified local image; no physical proof; `../evidence/E0009-fresh-windows-clone/` |
| E0010 | Repository-pinned CMOS5L qualification | GDS, 2 gate-level tests, and all 9 prechecks PASS; E0006 metrics and non-timestamp GDS records reproduced | Target timing is not Fmax; functional gate simulation is not silicon evidence; `../evidence/E0010-pinned-cmos5l-run/` |
| E0011 | Node 24 fast-CI action qualification | All 7 stages and artifact upload PASS; 0 annotations; locked image identity unchanged | CI orchestration only; no new physical or silicon claim; `../evidence/E0011-node24-fast-ci/` |
| E0012 | Readable M0 waveform qualification | Clean CI passes 2 tests, checks all 1,561 rising edges, and rejects an intentional corruption | Same finite Icarus simulation, not a new independent chip-behavior proof or owner-fluency result; `../evidence/E0012-readable-waveform-ci/` |
| E0013 | Conservative fluency-status qualification | Clean CI passes all 9 stages and rejects an unearned active-milestone fluency promotion | Validator integrity is not human understanding or ASIC evidence; `../evidence/E0013-fluency-status-ci/` |
| E0014 | Docker-independent M0 lesson qualification | Clean Windows host lessons, all 9 locked Linux stages, artifact upload and docs PASS with zero annotations | Reading retained evidence is not EDA execution, Docker repair, or owner-fluency evidence; `../evidence/E0014-docker-independent-learning/` |
| E0015 | Local Docker qualification | With Docker Desktop opened, signed version 4.92.0 and Engine 29.8.0 run the locked workbench; all 9 local stages PASS | A closed application is not a failure; no Docker-data, physical or fluency claim; `../evidence/E0015-local-docker-qualification/` |
| M1-local | M1 implementation candidate | Python semantic checks, Icarus/Verilator trace comparison, formal proof/covers/mutation and generic synthesis PASS locally | Working-tree result pending exact-head CI; preload is not reload and no CMOS5L result exists |
| M1-reload-local | Public-pin reload candidate | Icarus and Verilator load/read/run programs A and B after reset; store proof/covers PASS; generic synthesis reports 1,879 abstract cells | Exact-head CI passed at `d502227`; synchronous input assumption, no CMOS5L area/timing or silicon evidence |
| M1-input-wait-local | Synchronized bounded-input-wait candidate | Nine model checks and five tests on both simulators PASS; engine/store/synchronizer proofs and covers PASS; mutant rejected; generic synthesis reports 1,985 abstract cells and 321 state elements | Exact-head CI passed at `14a93b4`; primitive only at that revision; metastability and physical results remain NOT_EVALUATED |
| K-INPUT-WAIT-local | Three-word public-pin-loaded kernel | Same 96-bit image is loaded/read twice; independent event and timeout traces HALT at PC2 within six accepted edges on Icarus and Verilator; formal/lint/checks PASS; generic synthesis reports 1,971 abstract cells and 322 state elements | PASS/MEASURED at RTL rung and exact-head CI `f383744`; analog, CMOS5L, gate-level and silicon evidence NOT_EVALUATED |
| K-BOUNDED-LOOP-local | Four-word public-pin-loaded counted SET block | Counts 0, 1, 2 and 255 plus overflow target rejection match independent traces on both simulators; maximum produces 510 body edges and HALTs on edge 512; formal/lint/GL-shaped harness checks PASS | PASS/MEASURED at the RTL rung; 2,175 abstract cells/341 state elements after review fixes; exact-head CI/review and merge `b3b73e6` complete; physical evidence NOT_EVALUATED |
| M1-waveform-provenance-local | Separate and checksum-bind retained Icarus traces | Full eight-test 15,465 ns trace remains intact after the separate 11 ns GL-shaped smoke; deliberate overwrite and label-swap tests are rejected; all 11 evidence-collector stages pass | Evidence-integrity result only; exact-head CI/review and merge `2326022` complete; no gate-netlist, physical, silicon, or protocol claim |
| K-SHIFT-8-local | Three-word public-pin-loaded LOOP/SHIFT_STEP kernel plus public TX/RX registers | Both bit orders send eight bits and reconstruct RX in ten accepted edges; the full 11-stage collector passes 11 cases on both simulators, 16 model checks, waveform provenance, proofs/covers/mutant and generic synthesis; result capture occurs on the eighth step | PASS/MEASURED at the RTL/formal rung at implementation head `d1ddc8a`; 2,534 abstract cells/385 state bits, +359/+44 over K-BOUNDED-LOOP; exact-head CI/re-review passed and PR 4 merged at `081a8b1`; physical/protocol evidence NOT_EVALUATED |
| P-UART-TX-8N1 | Eight-word public SET/WAIT/LOOP/SHIFT_BURST program with two alternating payload slots | All complementary byte pairs at exact period in model; pin oracle covers full byte alphabet plus retained exact-period RTL traces; formal proof/covers/mutant and generic synthesis pass; independent review clean | E0016; final head `229c97c` passes push/PR CI and docs; PR5 merged at `80975ed` with post-merge CI PASS; PASS/MEASURED only at the digital RTL/formal rung; 2,783 cells/410 state bits, +249/+25; RX/electrical/CMOS5L/gate/silicon NOT_EVALUATED |
| P-UART-RX-8N1-semantic | Proposed eight-word WAIT_PIN/WAIT/SHIFT_BURST/LOOP receive/check witness | Frame/schedule oracle and existing semantic model agree on exact capture/check/HALT edges, byte alphabet, retained phase corners and bounded framing failures; generator rejects timeout overflow | E0017; PASS/MEASURED for reference execution only, timing formulas DERIVED; no production RTL delta; raw-valid-before-stop and overwritten first result are explicit limitations; mandatory RX RTL/delivery result remains NOT_EVALUATED |
| P-UART-RX-bounded-last | Same eight-word firmware plus generic runtime register readout | Pin traces pass capture-before-validation, final byte, phase/alphabet, framing/timeout and abort/reload on both simulators; corrected local/clean collector and independent re-review pass; initial failures retained | E0018; implementation `181cfa1` passes push/PR CI and docs, PR7 tracks final-record exact-head CI/integration; generic 2,793 cells/410 state bits (+10/+0); no retained-two-byte/continuous delivery, accepted flag, physical, analog or silicon result |
| P-UART-RX-host-service | Existing two-frame firmware with external tentative first-byte cache and terminal pair acceptance | Focused/reference, integer SMT safe/weakened checks, all 11 local/clean CI stages and independent review PASS at `9379d68`; 20 groups per simulator | E0019; bounded digital PASS/MEASURED; PR8 tracks final-record exact-head CI/integration; H+L<=10P DERIVED, external two-byte/control storage excluded from chip cost; generic unchanged 2,793 cells/410 bits; no RTL delta, autonomous/continuous, async-host, pad/CMOS5L/silicon claim |

## Open questions

- Q1: What timing quantum and external-input latency meet useful protocol rates?
- Q2: What program-memory type/capacity fits after physical overhead?
- Q3: How are programs and payloads loaded/read back after fabrication?
- Q4: What electrical assumptions and synchronization delays govern each pin?
- Q5: Which stretch protocol demonstrates the most reusable capability per cost?

## Rejected approaches

A registered engine-to-RX-store completion handoff was screened and rejected:
it used 394 state bits versus 385 for same-edge combinational completion and
introduced a hidden commit edge, although its generic screen used 2,512 rather
than 2,534 abstract cells. This transient working-tree ablation has no retained
standalone artifact and is not physical evidence. Protocol-specific fixed
blocks remain a useful cost baseline but are not the intended reprogrammable
competition solution. Do not retrospectively label unexplored alternatives as
experimentally rejected.
