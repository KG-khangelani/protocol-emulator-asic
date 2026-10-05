# E0018 - Public-pin bounded RX and nonintrusive readback

Base main: `3797c5a18771e413ecbe43e69541fece33b7bbd6` (PR6). D18 narrows
delivery explicitly: both frames must validate, but only the final byte is
retained/delivered after HALT. The first is discarded, not secretly queued.
Raw-valid is diagnostic capture, not acceptance; any FAULT rejects the batch.
Enable/reset/loader interruption requires host abort/reset/reload.

The production change is generic: `ui_in[7:5]=011` selects an existing data
register on dedicated `uo_out`; `uio` remains GPIO-owned. No UART-specific
executor path, opcode, FIFO, interruption/error flag or storage is added.
`src/config.json`, official ports/source list and 6x4 allocation are unchanged;
pin descriptions and the candidate datasheet now describe readback accurately.

## Focused behavior and initial aggregate failure

The locked workbench command below passes the public scenarios in 18.86s;
`focused-results-icarus.xml` retains the report. Frame expectations come from
mathematical input/schedule functions, never `Machine.edge`.

```text
make -C test COCOTB_TEST_MODULES=test_uart_rx_public SIM_BUILD=sim_build/icarus-rx-focused COCOTB_RESULTS_FILE=results-rx-focused.xml
sby -f -d build/public-readout-focused formal/m1_public_readout.sby
```

Coverage is the full complementary byte alphabet once at P4; P434 retained
`00/ff`, `ff/00`, `55/aa`, `aa/55` with quarter-phase corners; raw readback just
before/on both commit edges; writable-address runtime selection held across
execution; final delivery/status/GPIO retention with either enable; first and
second bad stop; first and second missing start; high-at-start-center; disable
of an incomplete second frame followed by reset and successful reload. Runtime
settles are budgeted inside exact 20,000ps clocks. Coincident transitions are
ordered 1ps before the clock, not claimed as real pad setup/hold safety.

Initial coherent `make check evidence` at
`build/evidence/20261005T080421477541Z` FAILS overall. Its source hashes and
actual statuses are retained in `initial-failed-manifest.json`: both simulator
regressions, engine/store/sync/readout formal checks and generic synthesis pass,
but lint rejects `always @*` in the FORMAL-only block and waveform provenance
rejects the newly expanded two-module regression. See both initial failure
logs. They are not rewritten as passes. Independent review identified the
provenance integration blocker and found no other RTL/policy defect.

Fixes use `always_comb` only inside FORMAL (production remains Verilog) and
require exactly `test` plus `test_uart_rx_public` for a full RTL label. A focused
validator check still rejects either subset, unknown modules, label swapping
and later waveform overwrite; existing gates are preserved. Lint and
provenance against the existing complete artifacts then pass. A fresh aggregate
collector and independent re-review are required before qualification.

Corrected `make check evidence` passes all eleven collector stages at frozen
working-tree run `20261005T081316859689Z`, with engine proof in 161s wall time. Curated
`local-manifest.json`, both simulator JUnit reports, waveform provenance and
formal log/statuses preserve source hashes and actual outcomes. The model and
provenance checks run in `make check`, not the collector's static stage. Both
simulators pass the required existing regression plus public RX scenarios;
all ten formal statuses pass including expected mutant rejection. Independent
integration re-review is clean (`review.md`). Exact committed-head CI remains
the publication gate; this local manifest correctly records a dirty tree.

Clean implementation head `181cfa19b2d05f0892bfb8e6ebb5e234b9a18f03` passes
push test [37283077006](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37283077006),
PR test [37283087343](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37283087343)
and docs [37283077101](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37283077101).
Downloaded collector `20261005T082447572530Z` records a clean checkout and all
eleven passing stages. All 31 collected artifact hashes and 130 committed-source
hashes were checked. CI's generic netlist independently recounts the same
2,793/410 resource totals. `ci-manifest.json`, both CI JUnit reports and
`qualification.json` preserve identities. The GitHub-reported ZIP digest is
recorded but not independently checked; bulk remains under ignored `build/`.
CI artifact expires 2027-01-03; curated evidence here persists with the source.
The final documentation record revision requires its own exact-head CI before
normal merge. [PR7](https://github.com/KG-khangelani/protocol-emulator-asic/pull/7)
tracks that final source, CI and integration independently of this historical
implementation qualification record. No untested merge head is inferred green.
The documentation-only revision passes the focused static metadata check and
independent evidence-record review. One terminal transport attempt failed
before that static process launched; a read-only checkout check confirmed the
unchanged workspace/head, and the scoped retry passed. No runtime/OS repair or
security change was performed; the unlaunched attempt is not counted as a pass.

## Resources and proof boundary

Generic Yosys screening initially reports 2,793 abstract cells and 410 state
bits: +10 combinational cells, +0 state versus E0016's 2,783/410. Engine remains
1,003 cells/108 bits; program store 1,646/261; data store 84/25; synchronizer
16/16; top glue 44/0. Program usage is eight 32-bit words (256 bits). This is
complete-chip structural accounting, NOT IHP area, physical fit or Fmax.

The added proof checks public combinational decode, GPIO/loader ownership and
load/reset gating. It does not formally prove integrated RX liveness. Required
existing formal proofs/covers/mutation and dual-simulator aggregate CI remain
the coherent release gate, not extra per-iteration test-count targets.

Complete retained-two-byte/continuous receive, analog baud tolerance,
metastability/MTBF, CMOS5L, gate-level and silicon are NOT_EVALUATED. M0 owner
fluency remains PENDING. Next: freeze bounded host-service deadlines/delivery
semantics for preserving both bytes before considering more storage.

The verified first-stop and second-capture edges differ by `9P=3906` clocks,
78.12 us at the target clock. This DERIVED availability window is a candidate
host-service bound, not a tested two-byte delivery guarantee or physical access
delay. The next contract must include host read latency and batch failure handling.

The official competition page was rechecked on 2026-10-05: open-source,
reprogrammable protocols, CMOS5L, current 6x4 maximum, deadline 2027-01-18
remain stated. Source: https://blog.janestreet.com/protocol-emulator-asic-competition/
