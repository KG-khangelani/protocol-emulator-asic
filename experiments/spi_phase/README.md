# SPI phase/capacity experiment

This directory implements **experimental copies**, not the production VM.
The [frozen contract](../../docs/specs/spi-phase-comparison.md) defines the
encodings, accepted-edge timing, loader bounds and compatibility differences.
The independent SPI pin oracle lives in `tools/spi_mode0_oracle.py`; it does
not decode candidate RTL or derive expected traces from candidate execution.

Inside the existing locked workbench, run:

```sh
python3 experiments/spi_phase/run_comparison.py
```

The runner refuses to overwrite an attempt, checks the E0020 production hashes,
generates isolated baseline/compact/banked RTL under ignored `build/`, runs
reference and public-pin tests, and synthesizes the entire chip identically.
It retains exact generated sources, patches, commands, JUnit, logs and generic
netlists. It rejects missing/skipped/unexpected test failures, input drift and
latches. Generic state bits count mapped one-bit DFF primitives recursively
from the top; cell count includes loader, stores, synchronizer and executor.

The original length-nine rejection test must fail only for the banked variant;
the runner preserves that failed JUnit and labels compatibility FAIL. A green
comparison means this predeclared difference was measured, not that the loader
is compatible. Production formal/physical proofs do not cover experimental RTL.
No experiment writes `src/`, edits the compiler or changes the visualizer.

The separate formal slice runs with:

```sh
python3 experiments/spi_phase/run_formal.py
```

It proves the [phase assertions and legacy refinement](../../docs/specs/spi-phase-formal.md)
in generated copies, retains reachability and deliberate-mutation witnesses,
and records actual task mode/depth and induction results. Formal-only readout
instrumentation has a checked inverse transform; it adds no state or inputs.
The original production `make formal` job remains separate. Failed/unknown
proof attempts are retained rather than converted into passes by the runner.

The integrated boundary runs separately:

```sh
python3 experiments/spi_phase/run_integration.py --with-simulation
```

It checks the actual compact top, public loader, full program/data stores and
two-stage synchronizer under the [integration contract](../../docs/specs/spi-phase-integration.md).
Universal safety, bounded public-loaded witnesses, reachability, expected
falsifications and four public-pin simulation groups per simulator have separate
records. Simulation uses uninstrumented candidate sources. Loader abort resets
execution while retaining an old completed result; payload writes invalidate
valid only. E0023 records that lifetime and the initial failed attempts.

The eight-word external-pin experiment runs with:

```sh
python3 experiments/spi_phase/run_pin_qualification.py
```

Its [pin contract](../../docs/specs/spi-mode0-pin-qualification.md) separates
full-program public-pin simulation, actual-synchronizer transport proof and
inconclusive direct full-chip SAT attempts. Independent pin mathematics imports
no VM or encoder; a separate reference test cross-checks the literal image.
The runner retains per-case response profiles, counts, timestamps, negative
controls and hashes, and requires identical public records on both simulators.
E0024 preserves the all-ones acceptance-guard failure and earlier tool/timeout
outcomes. The default CI job does not rerun the known full-chip SAT timeouts.

The separate actual-program invariant attempt runs once per invocation:

```sh
python3 experiments/spi_phase/run_program_invariants.py --output build/spi-program-invariants/new-attempt
```

The [attempt contract](../../docs/specs/spi-program-invariant-attempt.md) fixes
depth12 and a180-second wall limit. It keeps the real public-loaded eight-word
program and original input premises, adding proved loading/per-loop assertions
through reversible read-only taps. Four simulation preflights check the
assertions and premises before the single proof. The result distinguishes
induction, bounded/finite evidence and inconclusive attempts. CI additionally
requires an actual inductive PASS; E0024's previous timeouts are not rewritten.

The actual-program sensitivity gate runs separately:

    python3 experiments/spi_phase/run_program_sensitivity.py --output build/spi-program-sensitivity/new

It requires the inductive baseline, two reachable and inspected negative
traces, and six public transactions on each simulator. The early image is
loaded/read back against its supplied bytes before checking unchanged external
requirements. Expected solver FAILs remain labelled FAIL; the aggregate
accepts them only at the intended assertions and witness values.
--simulation-only labels finite controls; --reachability-only separates bounded
covers. [E0026](../../evidence/E0026-program-sensitivity/README.md) retains
successful controls, import failures and inconclusive reachability attempts.
