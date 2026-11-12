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

## Complete protocol regression

Both simulators pass all 30 required groups. Icarus takes 922.396 seconds;
Verilator takes 457.304 seconds, each within the declared 1,800-second limit.
Both reproduce the unchanged 1,052 SPI, 1,160 I2C, four boundary and 36 abort
records, plus all 44 expected bank-read observations. UART service/framing
and SPI input-hold expectations remain unchanged. `regression/` retains 994
files, including exact frozen inputs, both complete logs/JUnit files, every
record and the original reference bytes. Its standalone replay passes:

```console
python evidence/E0042-sram-prefetch-screen/regression/verify.py --output build/sram-regression-replay
```

The local simulator logs identify their actual versions. The completed
temporary container was removed before its exact image ID could be captured;
the archive states that limit explicitly. The separate clean-checkout CI
workflow retains same-job build/image/tool identity for its new runs. Its
proof/control and Verilator jobs have passed; Icarus is still running, and
the original CI archives require their own audit.

## Matched complete-chip mapping

The [predeclared screen](../../docs/specs/g2-sram-mapped-screen.md) runs only
after the complete simulator pair. It uses the same pinned physical image,
PDK, 8x4 footprint, 20 ns constraint and synthesis settings as E0040. D39's
reference reproduces its earlier result exactly. The only resolved setting
difference, after source-path normalization, is the added MACROS definition.

| Measurement | D39 reference | SRAM candidate |
|---|---:|---:|
| Standard cells | 34,683 | 4,200 |
| Flip-flops outside SRAM | 4,278 | 353 |
| Standard-cell area, square micrometres | 477,788.2578 | 53,089.7598 |
| SRAM macros | 0 | 1 |
| Macro footprint, square micrometres | 0 | 49,488.4992 |
| Complete mapped footprint, square micrometres | 477,788.2578 | 102,578.259 |

The complete mapped footprint falls **78.5306%**, clearing the declared 20%
threshold. The tool's 53,089.7598 area metric omits the black box; the total
above explicitly includes its actual LEF/library footprint. The mapped
netlist contains exactly `store.program_memory`, with the public clock,
reset-controlled enable, A_DLY/read enable high and all BIST inputs low.
Both runs have zero inferred latches, timing constructs, unmapped cells and
synthesis/check errors. The SRAM header inherits the vendor timescale,
causing 106 TIMESCALEMOD warnings on other modules; there are no other warning
types. The reference retains its one unused-signal warning. These logs stay
unchanged; remove the irrelevant black-box timescale in the next flow setup.

`mapped/` retains 144 exact inputs/outputs, including both real netlists,
settings, selected compressed timing libraries, logs, active container/image
observation and the independent area/connectivity audit. The 144-file replay
recomputes area from those libraries and validates all macro connections:

```console
python evidence/E0042-sram-prefetch-screen/mapped/verify.py --output build/sram-mapping-replay
```

Advance to a separately declared power/layout integration trial. Mapped area
is not routed area or timing acceptance. No routed/timing, precheck or
real-netlist pass is claimed; production is not promoted.

The [clean 95120d8 CI audit](ci-95120d8/README.md) now passes all three gates.
It retains and replays 1,359 original ZIP members, exact source, actual proof
models and negative witnesses, both 30-group suites, every reference record
and each producing job's loaded workbench identity. The earlier local runtime
receipt limitation remains documented separately.
