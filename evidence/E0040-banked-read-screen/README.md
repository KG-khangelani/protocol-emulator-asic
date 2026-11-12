# E0040 - Bounded banked program-read screen

Decision: [D41](../../docs/decisions/0041-retain-banked-read-alternative.md).
Predeclared [scope](../../docs/specs/g2-banked-read-screen.md).

The candidate uses sixteen eight-word selectors followed by a bank selector.
Only D39's combinational read block changes. Every clocked byte, all 128
words, the interface and the other four source files stay identical.

| Measurement | D39 parent | Banked read |
|---|---:|---:|
| Whole-chip generic cells | 15,211 | 15,593 |
| Whole-chip state bits | 4,278 | 4,278 |
| Icarus store-port checks | 1,178 | 1,178 |
| Verilator store-port checks | 1,176 | 1,176 |

Complete-store temporal proof passes within 240 seconds; the independent
reset base passes within 90. The actual models cover all 4,109 store state
bits and 54 output bits, with 4,150 bit comparisons including aliases and
134 reset vector assertions. All outputs are compared in every mode.

Both simulators reject the same deliberate high-bank alias, at PC120 after
real reset and 512 byte writes. Baseline success, successful mutant
compilation, the exact mismatch and nonzero simulation exit are retained.
Icarus also checks unknown low/high selector bits; Verilator's two-state
simulation is not credited with those checks.

The generic count rises 2.5113%; mapped and routed effects are **not
evaluated**. This is a retained alternative, not a promoted candidate or
complete-chip protocol qualification. A separate clock-routing diagnostic is
investigating the original layout before another implementation is selected.

`screen.tar.gz` contains 63 exact source, script, log, model and result files.
`archive.json` hashes every member; `SHA256SUMS` indexes the curated files.
Replay verifies the original bytes, actual state/output comparison coverage,
proof completion, synthesis counts and both observed mutation witnesses:

```text
python evidence/E0040-banked-read-screen/verify.py --output build/banked-screen-replay
```

The solver and simulator runs use the locked workbench. Replay audits retained
evidence; it does not rerun a solver or imply physical acceptance.
