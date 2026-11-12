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
| Mapped standard cells | 34,683 | 32,160 |
| Mapped area, square micrometres | 477,788.2578 | 502,643.5722 |
| Mapped buffers | 5,020 | 8,233 |
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

The generic count rises 2.5113%. The separately declared
[mapped comparison](../../docs/specs/g2-banked-mapped-screen.md) uses the actual
pinned physical runtime and library: the parent reproduces its earlier area
and cell count exactly, while the banked alternative costs **5.20216% more
mapped area**. Both preserve 4,278 sequential cells / 209,574.0864 square
micrometres and have zero inferred latches, unmapped cells or synthesis errors.
The candidate is set aside without a routed trial. No routed/timing or
complete-chip protocol qualification is inferred for this alternative.

`screen.tar.gz` contains 63 exact source, script, log, model and result files.
`archive.json` hashes every member; `SHA256SUMS` indexes the curated files.
Replay verifies the original bytes, actual state/output comparison coverage,
proof completion, synthesis counts and both observed mutation witnesses:

```text
python evidence/E0040-banked-read-screen/verify.py --output build/banked-screen-replay
```

The solver and simulator runs use the locked workbench. Replay audits retained
evidence; it does not rerun a solver or imply physical acceptance.

`mapped/mapping.tar.gz` retains 123 exact files, including both actual mapped
netlists, logs, resolved settings, source bytes and runtime identity. Its replay
also compares the original D39 settings after documented path relocation and
the explicit four-thread setting used by the original command:

```text
python evidence/E0040-banked-read-screen/mapped/verify.py --output build/banked-mapped-replay
```

E0041 separately diagnoses D39's clock-routing failure; this evidence does
not replace that original failed physical result.
