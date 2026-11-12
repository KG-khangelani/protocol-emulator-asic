# Executable backlog

Priority is set by [the six goals](goals.md), adopted in
[D32](decisions/0032-goals-to-submission-readiness.md) on 2026-11-12.
**G1 is complete.** D35 selects compact10's qualified
experimental physical pilot for the next integration step. At 29f4b73 it passes
GDS/routed metrics, all ten official prechecks and twelve real-netlist public
groups with 1,052 unchanged SPI records. P saves 13.1456% routed standard-cell
area but fails one fanout limit; its dependent jobs are skipped. E0031 retains
both original archives, matched configurations and earlier unsuccessful trials.
Alpha.5 publishes both candidates' evidence; all 28 release assets, exact image
identity and anonymous access are verified. All six tag workflows pass.

**G2 is active**, authorized on 2026-11-12 with commits throughout the work.
D36/E0032 freezes/tests the independent I2C oracle: 19 groups, 3,902 observations
and 53 retained witnesses. E0033 measures unchanged compact10: ten identical
records per simulator, ten-word bounded cleanup, expected held-SDA faults and
122-word literal write footprint versus a real ten-word store.
E0034 confirms existing SHIFT_STEP receive reuse: nine words,
268 identical records per simulator, all bytes and four rejected controls;
98,619.329 Hz, no full I2C framing or cleanup qualification.
D37/E0035 now advances od128: both simulators agree on 1,160 complete I2C records
and pass twelve public kernel/UART/SPI groups with 1,052 unchanged SPI records.
Current boundary checks, scoped instruction proofs and cleanup equivalence pass.
The 96-word combined image uses a real 128-word store, versus 211/255 literal
words. E0036 audits all three clean 31ebf82 G2 jobs and their downloaded
archives; both candidates now pass the full I2C matrix in both simulators.
Complete partitioned store induction now passes 652/1,287 assertions with
checked reset-reachable mutations. The exact eighteen-group selection passes
both simulators at e2ff52e. literal255 fails pinned 8x4 placement at 111.564%
adjusted utilization. od128 maps to 39,806 cells / 564,744.3984 square micrometres
but fails global routing with GRT-0228 congestion; dependent jobs are skipped.
E0036 retains original archive identities, runtime/configuration checks and
failure logs. All five clean
d3c340f CI gates and downloaded-evidence audits pass, including the complete
100-task store run. D38/E0037's explicit byte-lane store passes all 652 assertions
and both reset-reachable mutation controls. Both simulators pass all eighteen
public groups with exact reference records; retained replay and physical
staging preflight pass. All seven e5eef5b CI jobs pass and both new-candidate
archives are audited. Physical run43241097269 at 869ee34 fails global routing
with GRT-0228 congestion; precheck/netlist jobs are skipped. Verified archives
measure 40,242 mapped cells / 561,244.4208 square micrometres, only 0.620% less
mapped area than original od128. E0037 retains the failure and unchanged inputs.
A separate shared-read screen saves 37.64% generic cells from D38; both its
conditional store and reset-reachable complete-chip equivalence pass. Qualify
its public behavior before any separate physical trial. D39/E0038 freezes the
new candidate; its fresh complete-chip proof/reset base and all three public
mutation controls in both simulators pass. Both simulators now pass all eighteen
public groups with identical records. The 1,030-file retained replay, ten audit
corruption controls and physical staging preflight pass. All nine b774915 CI
jobs pass and both shared-candidate ZIPs are audited. Physical run43249867361
at 426cea1 maps to 34,683 cells / 477,788.2578 square micrometres, saving
15.3974% mapped area versus original od128, but fails global routing with
GRT-0228 congestion. E0038 retains the verified failure; dependent jobs are
skipped. D41/E0040's banked-read screen passes complete-store equivalence,
reset and both simulators' port/mutation checks, but adds 2.5113% generic
cells. Matched pinned mapping reproduces D39's original cost exactly and
shows 5.20216% more area for the banked candidate; set it aside without routing.
E0041 retains the first clock-spacing timeout at 1,200 seconds / iteration
40/50. The separately declared 2,400-second follow-up finishes with 159,781
overflow / 152.09% Metal3 usage. Stop the clock-spacing-only branch. Next,
declare and test synchronous SRAM loading/fetch semantics before a separate
candidate and physical-flow decision. Acceptance limits remain unchanged.
D42/E0042 now declares 0x22 clocked program reads and implements the real SRAM
candidate. Compositional engine/reset and arbitrary-word real-memory proofs
pass, with four coverage witnesses and a checked stale-lane fault. Both
simulators pass store-port checks and expose four actual faulty variants.
The historical 22-group suites and retained screen replay pass; both earlier
whole-chip timeouts remain visible. Both simulators now pass all 30 SRAM groups
and exact reference records plus the 44-byte bank control. The 994-file replay
passes. Matched mapping reproduces D39's reference exactly and measures
102,578.259 square micrometres including SRAM, 78.5306% lower. The actual
netlist has one macro and 353 flip-flops; the 144-file mapped replay passes.
The three SRAM CI jobs and their complete original-archive audit pass, retaining
1,359 original files and exact source/runtime bindings.
No production or routed/timing/precheck/actual-netlist acceptance is claimed.
D43/E0043 retains the native power-grid failure and its exact cause: 0.480
micrometre gaps leave all 104 supply rectangles unpowered. An isolated repair
adds 144 short outer-edge segments, preserving all placements and net/pin
assignments. Both fresh grids pass; the 260-file replay reconstructs the exact
database and repeats those checks. Two explicit added flow stages now pass a
fresh 31.625-second pilot and reproduce that exact database. All 80 original
stages remain in order. The first two full runs clear routing but fail the same
nine extracted SRAM-input slew limits; remaining checks were stopped and all
results retained. A stricter global diagnostic fails; a nine-buffer local
screen clears fresh typical estimated violations, preserves connectivity and
exposes both actual wiring faults. The 1,744-file replay passes. Finish and
audit the fresh buffered full run through the remaining manufacturing checks.
Its extracted electrical limits now pass at all three declared model sets with
positive setup/hold margins. Portable official staging reproduces the exact
power database; six corruption controls and the 742-file replay pass. Launch
and audit `gds-sram`; complete local netlist results are still pending. Physical
acceptance stays open.
The retained default-integration probe has four obsolete expectation failures.
D40/E0039 adds the explicit current profile: all 30 groups pass in both
simulators with exact records; the original source still passes all 22 groups
in both. The initial current and complete historical formal runs pass, but a
normal-command proof rerun reaches its 300-second limit. Seven other stages
pass; the 1,717-file retained replay preserves both outcomes. An isolated
metadata-cache counterexample is fixed by running repository checks fresh;
all 114 checks pass. Current-command CI passes at 8488738/run43267588725;
the original 1,532-file ZIP, 250 exact inputs and all eight stages are audited.
Physical closure, adoption and publication remain required. Production is unchanged. A fresh-checkout
unit-test setup failure is fixed in 6ec83ae; replacement test CI passes.
Historical builders now use an explicit E0020 source archive; guarded
regeneration reproduces every prior candidate without reading production RTL.
This prepares integration without promoting an unqualified design.
G2 covers the shared-core protocol set, G3 the assembler, G4 final publication,
G5 bounded optional novelty, and G6 owner fluency. Production promotion still
requires combined regression and fresh physical evidence. Historical task
evidence below is preserved.
The [I2C acceptance contract](specs/p-i2c-controller-100k.md) is frozen without
an ISA change. Experimental public-loaded I2C and combined results are retained;
the complete-store and exact physical-selection gates pass locally and in CI.
Physical qualification and production promotion remain pending.

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

Supporting documentation may advance independently of app design approval and
owner learning. Publishing a proposal does not satisfy an implementation gate.

| ID | Work | Exit gate | State |
|---|---|---|---|
| UI-T01 | Source-backed compact Protocol atlas and relationship tracing | Functional/source/edge/accessibility/browser verification in light/dark | Integrated via PR9 at `ae13f6b` on 2026-10-14; all three post-merge workflows PASS, including 18 source/model and 15 Chromium cases. UI0001 retains earlier results/failures; exact integration record on PR9. No visualizer source/data change or fresh local browser claim in the November SPI slice. Broader platform/device coverage NOT EVALUATED; no chip/learning promotion; PR8 integration tracked under M2-T01 |
| M1-T01 | Define execution, PC, reset, I/O, WAIT and HALT semantics | Reviewable cycle tables and invalid-program behavior | Implemented candidate in `specs/m1-execution-contract.md`; encoding remains provisional |
| M1-T02 | Implement SET/WAIT/HALT and independent reference model | Exact timing regression plus reset/PC/wait properties | Implemented candidate; local dual-simulator/formal/generic synthesis pass |
| M1-T04 | Public-pin program load and readback | Program A/reset/program B public-pin trace; invalid image fail-closed | Qualified at `d502227`: exact-head CI passes P-RELOAD simulation and store proof |
| M1-T05 | Synchronize inputs and add bounded event wait | Two-stage latency, final-edge event priority, timeout and enable freeze checked | Qualified at `14a93b4`: exact-head dual-simulator/formal/generic synthesis CI pass |
| M1-T06 | Execute K-INPUT-WAIT as a public-pin-loaded kernel | Same image takes event/timeout paths and HALTs within declared bounds against independent traces | Qualified at `f383744`: exact-head CI passes complete locked ladder |
| M1-T07 | Execute K-BOUNDED-LOOP as a public-pin-loaded kernel | Counts 0, 1, 2 and 255 produce exact bounded traces and HALT | Qualified by exact-head CI and independent review; PR 2 merged at `b3b73e6` |
| M1-T08 | Preserve simulation waveform provenance | Full RTL and GL-shaped smoke FST/JUnit pairs retain distinct paths, stage labels and verified checksums | Qualified by exact-head CI and independent review; PR 3 merged at `2326022` |
| M1-T09 | Execute K-SHIFT-8 as a public-pin-loaded kernel | Both bit orders, exact ten-edge bound, RX readback, data-register and partial/error behavior match independent expectations | Qualified at `d1ddc8a`; exact-head CI/re-review passed and PR 4 merged at `081a8b1` |
| M1-T03 | Add GET and BRANCH only as needed; bounded LOOP was evaluated by M1-T07 | Bounded behavior; cost delta recorded | D37/E0035 evaluates general WAIT_PIN failure branching with full-width destination and partial-operation cleanup; scoped induction, public boundaries and complete I2C programs pass. E0036 closes the actual-store proof; literal255 fails fixed-footprint placement and od128 physical qualification remains open. No GET opcode needed |
| M2-T01 | UART waveform oracle and VM transmit/receive | Randomized payloads, framing/error cases and timing checks | TX PR5 merged at `80975ed` (E0016); RX semantic PR6 merged at `3797c5a` (E0017); bounded last-byte PR7 merged at `155e130` (E0018); D19 host-serviced pair H+L<=10P and unsafe-overwrite counterexample pass local/clean CI and independent review at `9379d68` (E0019), PR8 merged at `7b2f746` after complete corrected-head PR CI at `996b967`; historical E0019 results preserved; no RTL/storage delta; continuous/autonomous delivery open |
| M3-T01 | SPI and I2C on shared core | Direction, sampling, stretching and contention cases | Active compact qualification. D22/E0021 cost/legacy limits, D23/E0022 core rules, D24/E0023 actual integration safety and D25/E0024 pin simulation retained. D26/E0025: actual public-loaded eight-word written-program induction PASS at step9 with configured depth12/180s; complete loading/per-loop state facts are proved assertions, original driver/assumptions unchanged. Four finite preflights PASS; initial generated-declaration failure retained. E0024 direct444-step timeouts remain INCONCLUSIVE, not overwritten. D27/E0026: baseline induction and two checked formal negatives qualified; six public cases per simulator PASS with identical records; clean implementation0eaa54c sensitivity CI PASS with verified artifact/source hashes. Terminal covers inconclusive (timeout/interruption); initial harness failures retained. D28/E0027: four-mode contract/oracle and6,176 reference positives pass; delayed SAMPLE saves one word under input hold, yielding8-word modes0/2 and10-word phase1 references. Both simulators pass36 scoped public cases each with identical records; clean a3bfcea expanded SPI CI PASS, artifact/source hashes verified. D29/E0028: actual held mode0/2 program induction PASS at step9 with symbolic bytes/order/CPOL;12 finite preflights and2 checked reachable negative controls pass. D30/E0029: bounded6,920-schedule screen finds nine-word mode1 and ten-word mode3 references, with3,072 model positives; both simulators reject108 shortened images plus four oversized commits with identical records. Clean c54a795 SPI CI passes with verified source/trace identity; alpha.3 assets and public image verified. No eight-word fit in this family; no ISA minimum. D31/E0030: P fits both phase1 modes in8words, uses3,146cells/412bits versus matched compact10 3,589/477, and passes instruction/compact-refinement/actual-program proofs. Each simulator agrees on1,052 transfers per P/F/compact10. Clean19265ff CI qualifies both and selects P; all source/trace/cost identities verified. Alpha.4 assets/public package and full tag regression verified. F local timeouts and old encoding rejections retained. D34 official routed P saves 13.1456% standard-cell area but fails one fanout limit; compact10 clears GDS/routed metrics and passes 12 real-netlist groups with 1,052 unchanged records. All ten official prechecks pass; D35 selects compact10 as the experimental physical pilot. No combined production protocol qualification is claimed. Candidate/production unchanged; PR11 merged at `1383158`; PR8 merged at `7b2f746`; compiler deferred; production SPI/I2C/physical unqualified |
| M3-T02 | Compare architecture and instruction ablations | Program bytes, cycles, mapped area and verification cost | E0021 measures encodings, store/loader capacity and complete-chip generic cost. E0031 now records matched P/compact10 mapped and routed cost, timing and actual storage; P fails fanout; compact10 passes all required physical gates and is selected by D35. Broader architecture comparisons remain queued |
| M4-T01 | Assembler, load/readback workflow and timing listing; temporal IR only as needed | Deterministic output, diagnostics, capacity/timing checks and clean-clone protocol examples | G3, queued after the instruction decision; develop alongside G2 |
| M5-T01 | Official physical closure, real netlist tests and reproducible final release | Same-revision GDS/precheck/timing/protocol evidence, clean rerun and verified release/package | G1 compact10 GDS/routed metrics, all ten prechecks and public netlist checks pass; alpha.5 publication and downloads verified. G4 final closure follows shared-core qualification |

Do not preallocate a program-memory size or promise a protocol bitrate before
measurement establishes feasibility.
