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
