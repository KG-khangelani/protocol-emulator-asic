# E0021 - Phase instructions versus more program storage

Observed: 2026-11-03, Windows KhanCreate, existing locked Linux workbench.
Rung: **isolated experimental RTL + CHIP_COMPLETE generic synthesis**.
No production source, pins/config, visualizer or learning-record change.

A bit must be put on the wire before the other end reads it. SPI mode 0 reads
on rising SCK and prepares the next bit during the low phase. E0020 showed that
one instruction doing both jobs can read a late reply too early. This experiment
asks whether separating those jobs can fit the existing eight-word store, and
what it actually costs compared with adding storage and a loader bank.

The [contract](../../docs/specs/spi-phase-comparison.md) freezes actual encodings,
atomic GPIO behavior, accepted-edge delays, invalid/mixed operations and bank
bounds. [D22](../../docs/decisions/0022-compact-phase-candidate-before-promotion.md)
selects the compact candidate for further qualification, with production held.
The existing independent external pin oracle judges both candidates; expected
SCK/CS/data never come from candidate RTL execution.

## Results

| Alternative | Words / used program bits | Generic cells | State bits | Response envelope |
|---|---:|---:|---:|---|
| Existing coupled, faster target | 8 / 256 | 2,793 | 410 | Conditional d<=88; d=89 FAIL retained |
| Compact DRIVE+aux / delayed SAMPLE | 8 / 256 | 3,107 | 412 | Tested through d=96 |
| Plain DRIVE/SAMPLE + banked store | 10 / 320 | 3,403 | 477 | Tested through d=96 |

d is target response in quarter-clocks at H=25, with a 50 MHz execution-clock
target. d=88 leaves 60 ns digital setup; d=89 leaves 55 ns and preserves E0020's
`0x69 -> 0xb4` MSB-first failure. d=96 leaves 20 ns setup. These deterministic
simulation assumptions do not establish electrical timing on a real board.
All alternatives use 403 accepted edges; phased capture is edge 379 versus
legacy 376. Both phased candidates generate the same declared SCK/CS trace.

Compact adds 314 generic cells and two flags; the banked alternative adds 610
cells and 67 bits, including 64 program bits and a bank bit. Compact saves 296
cells/65 bits against this ten-word implementation. Counts recursively include
top, loader/readback, program/data storage, synchronizer and executor. Identical
`read_verilog; hierarchy -check; synth; check -assert; stat; write_json` commands
and Yosys 0.67+111 were used. No latches/check errors. Primitive counts are an
unweighted generic comparison, not CMOS5L mapped cell area, timing or Fmax.

The frozen final runner passes all 12 stages. Four model cases cover 1,024 byte
transactions across both candidates/orders plus capacity and control cases.
Each phased candidate passes **four RTL groups on each simulator**, including
519 real public-loaded/read-back transfers per run: every RX byte with
complementary TX in both orders, retained response corners and H=4. Across the
two candidates/simulators this is 2,076 public transactions. Assertions check
exact 20,000 ps clocks, every GPIO/OE edge, independent wire decoding, capture and
HALT. Other cases check partial/mixed faults without false commit, latched delay,
enable freeze, reset, legacy payload-slot interoperability, auxiliary masks,
reserved bits and bank out-of-range non-aliasing/commit bounds.

The unmodified 17-group legacy suite passes for baseline and compact. The banked
variant has **16 PASS / 1 FAIL**, exactly the predeclared
`test.invalid_length_never_releases_engine`: length 9 now commits successfully.
Its failed JUnit is retained and compatibility remains FAIL. Register 5 changes
from reserved to bank control. The comparison's green status means this
difference was measured; it does not turn the loader into a compatible one.
Compact intentionally makes new previously invalid instruction words legal.

## Reproduction and provenance

Start from prior draft head `463cc1e1c270018b8b63378f057deeeca51d6ee0` plus
the exact input hashes in [result.json](result.json). Inside existing locked
image `protocol-emulator-asic-workbench:2026-07-29`, run:

```sh
python3 experiments/spi_phase/run_comparison.py
```

The runner refuses output overwrite and production/input drift. Generated
sources, diffs, commands, full logs, JUnit and netlists remain under ignored
`build/spi-phase-comparison/attempt-05/`; CI independently runs the same runner
and uploads those inputs/outputs. It uses `+NO_DUMP`, preserving production
waveform provenance. No image pull/build, dependency install or cleanup ran
locally. Doctor passes the lock; `make check` passes 35 Python cases and the
metadata/learning checks; atlas export consistency passes.

[run-result.json](run-result.json) retains all commands/statuses/counts and
[source-manifest.json](source-manifest.json) identifies every generated RTL file.
[result.json](result.json) binds input/protected-source and original/curated
artifact hashes. Test/failure logs normalize LF/trailing whitespace only; failed
outcomes are unchanged. Synthesis logs retain final CHECK/statistics excerpts;
full logs/netlists remain in build/CI with original hashes recorded. Patch JSON
preserves exact diff text in its `patch` field; decode
that field before applying. Bulk generic netlists are kept in build/CI artifacts.
Curated JUnit/logs cover every final stage, including the expected failure.

Initial failures are preserved under [failures/](failures/): declaration-order
compile error (observed log not archived), two module-path failures, a strict
runner rejection of fourteen filtered bootstrap tests despite four passing
selected groups, and Verilator's four implicit-width warnings. The standard
test module and explicit one-bit parameter correct those issues without
weakening skipped-test or compiler-warning guards. The final frozen run passes.

## Decision and limits

Proceed with compact's formal qualification; keep production RTL unchanged.
Keep the existing no-RTL option under its explicit faster-target assumption.
No new formal proof covers these experimental phase operations. Four-mode SPI,
continuous multi-byte delivery, I2C, physical fit/timing, metastability and silicon
are NOT_EVALUATED. H1-H=4 remain unproven. PR8/compiler deferrals and pending M0
owner fluency are unchanged. New exact-head remote CI is tracked on draft PR11;
the older head's passes do not qualify this increment.

The [official challenge](https://blog.janestreet.com/protocol-emulator-asic-competition/)
was rechecked today: open-source/reprogrammable, CMOS5L, 6x4 and 18 January 2027
remain the pertinent constraints; possible 8x4 is still conditional.
