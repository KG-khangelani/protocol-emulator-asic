# E0039 - Current source verification profile

D40 prepares normal project commands for the exact D39 candidate while
production still uses the original source. The isolated default integration
failure remains in E0038. This record does not promote the RTL or supply
physical qualification.

The current suite keeps all default test identities, updates the four
explicitly obsolete expectations to the declared 128-word/eight-bit contract,
and adds the complete public protocol/boundary/abort selection. Both simulators
pass **30 groups**, including the directly driven engine, with identical
1,052 SPI, 1,160 I2C, four boundary and 36 abort/reload records. An additional
44-byte public readback control checks the highest word without aliasing low
words. The historical source still passes all **22 original groups** in each
simulator with the original limits.

Current formal checks bind the actual five candidate files to complete-chip
equivalence/reset, four general-instruction proof/cover/control tasks, five
support-unit tasks and the host deadline lemma. The complete ten original
formal tasks separately pass on immutable E0020 inputs at unchanged proof
depths. This preserves their historical scope; D38's complete-store proof and
D39's whole-chip equivalence remain necessary parts of the proof chain.

The `pipeline` archive contains the normal commands' stage receipts, source
identities, logs, models, witnesses, JUnit and public records. **Seven stages
pass; the formal stage is incomplete.** Its temporal equivalence rerun reaches
the unchanged 300-second wall limit, so no aggregate evidence PASS is written.
This does not erase the earlier successful proof, retained in the separate
`formal-success` archive, or turn the incomplete command run into a pass. The `inputs`
archive holds every source/configuration/reference byte bound into those
receipts, including the exact verifier code. `legacy-regression` retains the
two original 22-group runs and their driver. Initial direct-run summaries are
retained separately; the complete replay uses the normal-command artifacts.

The eight normal stages are doctor, repository checks, scoped style, Icarus,
Verilator, current plus historical formal, generic synthesis and the separate
RTL harness smoke test. Current RTL keeps public trace witnesses; only the
separate smoke emits an FST. That FST is not real-netlist evidence. Six unit
groups initially cover valid receipts and reject changed code/source/runtime, missing/modified/extra artifacts,
a rehashed skipped test, failed/running stages and an unknown source profile.
An isolated counterexample then shows that the original collector omitted
learning/history metadata from its cached repository check's input set. The
retained replay reproduces that defect using the frozen original code and
corrupted metadata, without changing the live repository. The installed repair
always runs repository checks fresh during collection; expensive stages still
require exact input/artifact matches. A seventh receipt test rejects reuse of
repository checks even with an otherwise matching receipt. All 114 repository
checks pass after the repair. A clean command-level CI run remains pending.

The retained input snapshot describes the initial command run and reproduces
its cache defect. The installed collector differs by the explicit freshness
repair in `cache-fix/`; do not present the initial snapshot as a complete
qualification of that final collector.

Reproduce the retained audit without rerunning the simulators or solvers:

```sh
python evidence/E0039-current-verification/verify.py --output build/current-profile-replay
```

To rerun the prospective profile in the locked workbench before adoption:

```sh
make SOURCE_DIR="$PWD/evidence/E0038-shared-program-read/sources/od128" \
  CURRENT_ARTIFACTS="$PWD/build/current-candidate" \
  doctor check lint test test-verilator formal synth evidence
```

The exact source remains `od128-shared`, ISA 0x21, 128 real words and 4,278
state bits. Generic synthesis is not CMOS5L area/timing. The pinned physical
trial now fails global routing, retained in E0038. All ten prechecks,
actual-netlist public selection, final artifact audit, production adoption and
milestone publication remain open. The profile is preparation for integration.
