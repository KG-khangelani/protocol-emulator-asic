# E0042 - Synchronous SRAM and look-ahead fetch screen

[D42](../../docs/decisions/0042-screen-synchronous-sram-with-prefetch.md) and
[the predeclared contract](../../docs/specs/g2-sram-prefetch-screen.md) start
an isolated implementation experiment after the mapped/routing rejections.

`feasibility/` retains the exact selected installed PDK model, core model,
datasheet and LEF bytes, compressed without edits, together with hashes of
all three timing libraries and the read-only inspection script. Copyright
and license notices remain in the original files. The selected 256x32 macro
occupies 49,488.4992 square micrometres; proposed logical capacity stays 128
words. This is a macro footprint, not a complete-chip cost or physical pass.

The initial inspection predates implementation. Its key constraints remain:
synchronous reads, no SRAM data reset, A_DLY tied high, unused BIST tied low,
and a fast-library temperature different from the current standard-cell
corner. The new 0x22 interface and any physical integration require the stated
proof, simulator, complete regression and signoff gates before promotion.

## Actual engine and store results

`candidate.json` identifies the five generated source files and both exact
vendor models. `screen.tar.gz` retains their bytes, proof models/scripts/logs,
port-test observations, real faulty implementations, historical-suite results
and failed attempts. `archive.json` binds each member; `SHA256SUMS` binds the
retained files. The compressed retention runner records the selection.

- **Engine refactor:** all 128 actual state bits and all 128 original output
  bits pass compositional temporal equivalence in 1.372 seconds and a separate
  reset base in 1.976 seconds. The 331 bit comparisons include aliases; they
  are not 331 distinct state bits. The surrounding D39 modules are byte
  identical in this comparison. The additional next-PC output and SRAM
  integration are separate obligations.
- **Store ports:** Icarus passes 2,462 checks, including two unknown-PC checks;
  Verilator passes 2,460 checks using its two-state model. Both cover all 512
  byte addresses, all lanes, disabled access, reset/reload, partial writes,
  bank/length boundaries, clocked reads, stale fetch tags and immediate PC0.
  Both expose all four actual faults: retained valid bits on reset, stale
  unwritten lanes, fetching current instead of next PC, and missing PC0 shadow.
  Each negative control compiles successfully and fails the expected observable
  check against a passing baseline.
- **Store formal:** 18 assertions prove the logical-word relation under free
  writes and resets, with one arbitrary 7-bit word index. The complete vendor
  256x32 digital memory remains in the model with unconstrained initial data;
  read-only probe ports expose its contents. Its write clock is the public
  clock after constant propagation of tied-off BIST. K-induction passes in
  3.581 seconds. Four coverage witnesses pass; an actual partial-write-mask
  fault produces a checked stale-lane counterexample. The sole assumption is
  the first sampled reset. This is a digital-model proof, not analog SRAM
  characterization.
- **Compatibility:** the original production source passes all 22 historical
  groups in both simulators with the opt-in SRAM helper disabled. Its input
  files are retained from the unchanged snapshots taken before that run.
  Repository checks pass all 114 tests.

Two complete-chip refactor attempts reach the predeclared 120-second temporal
limit. Both remain inconclusive; their logs, sources, scripts and omitted bulk
model hashes are retained. The specification records the subsequent switch to
compositional engine proof. Failed preparation attempts also remain: deleting
an aliased output, leaving a constant BIST clock mux unflattened, and omitting
the regression environment. None is counted as a passing experiment.

Replay the retained screen without rerunning solvers or simulations:

```console
python evidence/E0042-sram-prefetch-screen/verify.py --output build/sram-screen-replay
```

The complete 30-group SRAM protocol regression is running separately. No
complete-matrix, mapped-area, routed/timing, precheck or real-netlist pass is
claimed yet. Production is not promoted.
