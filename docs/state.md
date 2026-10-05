# Current state

Updated: 2026-10-05. Engineering phase: **M1 - reloadable sequencer**.
Learning phase: **M0 - fluency pending**. Hard deadline: **2027-01-18**.
Active engineering task: **M2-T01 bounded UART receive/public readback**. Active learning task: **M0-T01**,
[GitHub issue #1](https://github.com/KG-khangelani/protocol-emulator-asic/issues/1).

Research question: What is the smallest computational substrate that can
efficiently express useful digital communication protocols under hard temporal constraints?

## Established

- Official CMOS5L template retrieved; all 22 imported file blobs verified.
- Local Git `main` initialized with template import history.
- Public GitHub repository released after E0004 audit: https://github.com/KG-khangelani/protocol-emulator-asic
- Codex instructions, specifications, ledger, backlog and reproducibility commands created.
- M0 GPIO counter, cocotb tests and CI prepared.
- Local static checks pass; see `evidence/E0001-bootstrap/`.
- GitHub CI passed static, GPIO RTL regression, generic synthesis and docs build;
  see `evidence/E0002-ci/` for the tested source revision and result links.
- The E0002 CI ZIP is durably archived in the repository with a matching
  GitHub-reported SHA-256.
- Publication controls are enabled: GitHub secret scanning, push protection,
  Dependabot security updates and private vulnerability reporting.
- Docker Desktop is available locally: when opened, observed signed version
  4.92.0 runs Engine 29.8.0 on Linux/amd64, and E0015 passes all nine locked
  local evidence stages at a clean source revision. The owner clarified that
  Docker had simply been closed; no repair or runtime failure is claimed. Native
  Windows `make`, Icarus and Yosys remain absent by design.
- A locked Linux/amd64 Docker workbench provides exact-version checks, Verible
  lint, simulation and generic Yosys synthesis from Windows. E0005 records its
  initial Icarus validation; the current candidate also passes the same two
  tests locally with Verilator.
- The M0 formal suite locally proves the public-pin reset, count, wrap, hold,
  fixed-output, and ignored-input properties, reaches the wrap in a cover
  witness, and rejects an increment-by-two mutant.
- Locked fast GitHub run 36119276357 independently reproduces the full seven-stage
  ladder on a clean checkout: doctor, static, lint, Icarus, Verilator, formal,
  and generic synthesis all pass. E0007 durably retains the manifest, both JUnit
  results, formal logs, synthesis netlist, tool identities, and limitations.
- The first official CMOS5L run produced a GDS, positive setup/hold slack,
  zero reported route/Magic DRC and LVS errors, and passed every Tiny Tapeout
  precheck. See `evidence/E0003-cmos5l-first-run/`.
- The missing gate-level UDP model was added to `test/Makefile`; corrected
  official run 36111852179 passes GDS, both gate-level tests, and all nine
  prechecks. E0006 retains its metrics, hashes, raw summaries, and limitations.
- E0003 and E0006 have identical physical metrics and GDS geometry records.
  Their whole-file hashes differ because GDS timestamp records changed; this
  distinction is documented rather than reported as byte-for-byte reproduction.
- A scheduled read-only upstream canary reports when Tiny Tapeout's live CMOS5L
  action branch moves without changing the qualified pins. Its first remote run
  reports CURRENT and retains the observation in E0008.
- A fresh public-repository clone on Windows 11 passes the seven-stage locked
  ladder through the PowerShell wrapper with no native EDA commands on PATH.
  E0009 also confirms the physical-input byte hashes match Linux CI after LF
  checkout canonicalization.
- Clean repository-pinned physical run 36118046477 passes GDS generation, both
  gate-level tests, and all nine prechecks. E0010 records the exact source,
  action, support-tools, LibreLane, PDK, job, artifact, and report identities.
- E0006 and E0010 are two complete official physical-flow passes under the same
  resolved environment. Their metrics and 393,577-record GDS structures match;
  their exact GDS hashes differ only in 32 timestamp records. The technical M0
  physical gate is satisfied.
- `workbench.ps1 LearnM0` provides a read-only guided inspection of the archived
  RTL, fast verification, physical evidence, claim boundaries, and teach-back
  prompt. Its verification mode is part of the static check; it cannot mark
  owner fluency automatically.
- `workbench.ps1 LearnWaveform` reruns the real M0 Icarus regression as readable
  VCD, checks every rising edge against the transition table, rejects an
  intentionally corrupted edge, and prints the key reset/count/wrap/hold/resume
  rows without requiring a GUI waveform viewer.
- Clean GitHub run 36128227539 qualifies that learning command: both tests pass,
  all 1,561 rising edges match the declared M0 rule, and the intentional
  corruption is rejected. E0012 retains the exact waveform, log, JUnit report,
  manifest, hashes, and proof boundary; it does not satisfy owner teach-back.
- `workbench.ps1 LearnStatus` now exposes one conservative M0-M5 learning
  record: technical and fluency gates are separate, every criterion starts as
  `NOT_DEMONSTRATED`, and automation is forbidden from promoting human fluency.
- `workbench.ps1 LearnStatus` and `LearnM0` now have a Docker-independent,
  read-only host-Python path. Clean Windows job 108202843341 runs both lessons
  without invoking Docker; the companion locked Linux job retains all nine
  passing evidence stages. E0014 records the source, output, runner, jobs,
  artifact, annotations and claim boundary.
- With Docker Desktop opened, local run E0015 independently passes doctor,
  static, learning-status validation, lint, both simulators, the readable
  waveform, formal proof/cover/mutation, and generic synthesis. It does not
  rerun or replace the qualified E0006/E0010 physical results.
- Clean GitHub run 36130223560 passes all nine retained evidence stages and
  rejects a deliberately unearned fluency promotion. E0013 records the exact
  source, log, manifest, container identity and limitation; M0 fluency remains
  pending because validator integrity is not human understanding.
- Fast CI now pins Node 24-native setup-buildx v4.4.1 and build-push v7.4.0
  release commits. E0011 records a clean seven-stage pass, unchanged locked
  workbench image identity, successful artifact upload, and zero check
  annotations after the Node 20 warning was removed.
- GitHub now reports the pytest Dependabot alert as fixed after dependency-graph
  refresh recognized pytest 9.0.3; it was not manually dismissed.
- The pre-M1 architecture landscape now compares fixed RTL, PIO-style engines,
  the temporal-sequencer hypothesis and tiny CPUs against exact locked upstream
  sources. It makes no architecture selection and treats external result claims
  as `NOT_EVALUATED` until reproduced.
- The architecture evaluation contract now fixes complete-chip accounting,
  shared microkernel/protocol workloads, two-axis result labels, falsification
  gates and a non-weighted selection rule before candidate measurements exist.
  This completes R0 research without opening M1 or selecting an ISA.
- A proposed SET/WAIT/HALT execution contract now provides reviewable cycle
  tables, reset/enable priority, PC/GPIO/terminal-state behavior, and explicit
  verification obligations. Its Python model now serves as the independent
  oracle for the implemented M1 candidate; no M1 physical claim exists.
- By explicit owner decision, engineering now progresses independently from
  learning checkpoints; M0 fluency remains `PENDING` and unpromoted.
- The M1 candidate implements bounded SET/WAIT/HALT execution, safe FAULT,
  enable/reset priority, a provisional four-word preload, and independently
  checked pin traces. Local Icarus, Verilator, formal and generic synthesis pass.
- The constant preload is replaced by an eight-word public-pin store with byte
  writes, length commit, readback and bounded fetch. Local Icarus and Verilator
  each pass `P-RELOAD` for distinct programs A and B; store formal checks pass.
- Generic synthesis reports 1,879 abstract cells including 300 state elements,
  up from 225 cells for the preload candidate. This is a storage-cost screening
  result, not CMOS5L area or fit.
- The next M1 candidate adds a two-stage `uio_in` synchronizer and bounded
  `WAIT_PIN`. Both simulators pass five tests; engine/store/synchronizer formal
  proofs and covers pass; the wrong-WAIT mutant is rejected. Generic synthesis
  reports 1,985 abstract cells and 321 state elements. The shared loader/input
  pins require two disabled sampling edges before input-dependent execution.
  These are local pre-physical results, not `K-INPUT-WAIT` completion.
- Exact-head CI passes the synchronized input-wait milestone at `14a93b4`.
- A three-word, 96-used-bit public-pin-loaded `K-INPUT-WAIT` kernel now takes
  both event and timeout paths and reaches HALT at PC2 within six accepted
  execution edges. Reset erases it, the same image is reloaded/read back, and
  an independent public-pin trace distinguishes the paths. Both simulators and
  the full locked ladder pass locally. Generic synthesis reports 1,971 abstract
  cells and 322 state elements; this is screening, not physical evidence.
- Exact-head CI passes K-INPUT-WAIT at `f383744`.
- K-BOUNDED-LOOP was selected before K-SHIFT-8 because repetition is shared by
  every target protocol while shifting still lacks payload/readback contracts.
  A four-word public program passes counts 0, 1, 2 and 255 on both simulators;
  count 255 produces 510 body edges and HALTs on accepted edge 512. Formal
  checks cover loop setup, rewind, final exit, reset/freeze and invalid nesting.
  Generic synthesis after review fixes reports 2,175 abstract cells and 341 state elements: +204
  cells and +19 state bits over K-INPUT-WAIT, exactly matching the declared
  loop active/start/end/count state at the state-bit level.
- Independent review found and the candidate now fixes two release blockers:
  six-bit LOOP target arithmetic faults before a target above PC31 can alias by
  wrap, and cocotb initialization no longer requires direct-engine handles in
  `GL_TEST`. A lightweight GL-shaped RTL smoke verifies the harness boundary;
  it is not gate-netlist or physical-flow evidence.
- Exact-head CI and independent review passed the M1-T07 fixes; PR 2 was merged
  to `main` at `b3b73e6fc63b2b22c9f9bd2314fd9e7a97b6266a`.
- A post-merge evidence audit found that the 11 ns GL-shaped smoke overwrote
  `test/tb.fst`, which the collector then labelled as the full `rtl_icarus`
  waveform. M1-T08 gives the smoke a distinct FST, checkpoints
  the full regression before the smoke, rejects checksum or label drift, and
  archives each artifact under its actual producing stage. Exact-head CI and
  independent review passed; PR 3 was merged to `main` at
  `2326022cc9d8ff0135448341ca5d942a5bcfbe91`.
- K-SHIFT-8 acceptance is frozen before implementation in
  `specs/k-shift-8.md`. D15 composes an eight-bit transfer from one-bit
  SHIFT_STEP operations inside the existing bounded LOOP. A three-word public
  program sends and receives bytes in either bit order in ten accepted edges;
  TX payload and RX result/valid use public loader registers.
- The complete 11-stage locked evidence collector passes locally for the
  K-SHIFT-8 working-tree candidate: eleven tests on each simulator, 16 independent
  model checks, waveform provenance, lint, formal proof/cover/mutation and
  generic synthesis. Generic synthesis reports 2,534 abstract cells and
  385 state elements: +359 cells and +44 state bits over K-BOUNDED-LOOP. The 44
  state bits exactly decompose into 17 data-store bits and 27 in-progress shift
  bits. These are simulation/formal/structural screens, not physical evidence.
- Independent review found no apparent RTL defect but blocked release on two
  verification gaps: integrated same-edge RX visibility was only observed after
  HALT, and RTL/formal did not cover SET/WAIT preservation or byte extremes.
  The candidate now reads RX before another edge, compares interleaved and
  extreme traces against the model on both simulators, and formally holds shift
  state across every non-shift transition. Independent re-review is clean at
  implementation head `d1ddc8a`; both push- and PR-triggered exact-head CI runs
  pass. PR 4 was subsequently merged normally at
  `081a8b14a68ff58d46c3b75d53b7138dbea79433`; its post-merge test and docs
  workflows pass.
- P-UART-TX-8N1 acceptance is frozen in `specs/p-uart-tx-8n1.md`. The candidate
  uses an eight-word SET/WAIT/LOOP/SHIFT_BURST program and two public payload
  slots to emit distinct back-to-back frames. The model enumerates all 256
  complementary pairs at exact period 434; Icarus and Verilator check every
  byte in both slots at period two plus four retained exact-period pairs.
  Fourteen tests on each simulator, 18 model checks, lint, formal proof/covers/
  mutation, storage/synchronizer proofs and generic synthesis pass locally.
  Generic synthesis screens at 2,783 abstract cells and 410 state bits, a
  +249/+25 delta from K-SHIFT-8 after removing two redundant mode flags.
  Independent review is clean; implementation head `b0555df` passes push and
  PR CI plus docs. E0016 retains local and clean-source CI evidence. Only the
  frozen digital UART-TX workload is qualified; no physical or complete-UART
  claim is made. Final reviewed head `229c97c` passes push/PR CI and docs;
  PR 5 was then merged normally at `80975edabdc82ca8511ad09e2bacf79ebdf3b27f`.
  Post-merge test and docs workflows pass; E0016 retains the integration record.
- The next bounded milestone freezes the proposed UART-RX schedule in
  `specs/p-uart-rx-8n1.md`. An eight-word existing-instruction witness samples
  two frames at their centers and faults on absent start, high at start center,
  or bad stop. The independent mathematical waveform/schedule and existing
  model agree locally (E0017); no production RTL changes occur. Raw RX-valid
  precedes stop validation, and the single result register overwrites frame
  one. UART-RX RTL qualification and lossless delivery remain NOT_EVALUATED.
- D18 fixes a two-frame all-or-nothing batch that delivers only the last byte.
  A generic runtime selector exposes existing data registers on dedicated
  `uo_out` without resetting execution or driving RX. Public-pin checks match
  the independent frame/schedule oracle on Icarus and Verilator: both raw
  capture edges, final delivery, bad first/second stop, missing first/second
  start, high start center and disable/reset/reload. Raw-valid is not acceptance.
  The initial aggregate run passes functional/formal/generic screens but fails
  lint syntax and the stale single-module provenance validator; E0018 preserves
  these failures. The corrected frozen-tree aggregate and independent re-review
  pass; exact-head CI remains the publication gate. Generic screening is
  2,793 abstract cells/410 state bits (+10 cells, no new state versus TX).
  Complete retained-two-byte/continuous receive and physical closure remain open.

## Blocked or unverified

- The M0 owner fluency checkpoint has not yet been completed; technical closure
  alone does not satisfy the project's equal learning goal.
- The official composite action's internally tagged dependencies remain a
  recorded trust boundary. The upstream canary reports change but never upgrades
  the qualified environment automatically.
- No FPGA run or devcontainer validation exists yet. These are not M0 acceptance
  gates. Positive slack at the 20 ns target is not a measured maximum frequency.

## Next executable actions

- Engineering: qualify the bounded last-byte RX/public readout candidate after
  integration fixes, independent re-review and exact-head CI. Then specify a
  bounded host-service/delivery contract for preserving both received frames
  before adding storage. Keep focused risk-based checks during iteration and
  aggregate gates at review/merge milestones; no new physical claim is implied.
- Learning: complete the owner M0 teach-back when capacity permits; do not infer
  fluency from engineering progress.

## Handoff boundaries

M0's technical gate has passed and its fluency gate remains pending. The M1
candidate is reloadable through clock-synchronous public pins and has a local
UART-transmit firmware candidate and a bounded last-byte RX experiment. Complete
UART receive delivery, SPI and I2C remain unevaluated;
compiler, new physical closure, Fmax and fabricated-silicon claims remain
absent. The original OpenKnowledge records
named in `source-pack.md` were not modified or synchronized by this setup.
