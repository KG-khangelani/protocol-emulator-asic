# E0044 - Source-matched normal verification for the SRAM candidate

D44 adds `od128-sram` to the normal verification commands while leaving production
unpromoted. The profile identifies the five exact E0042 source files, both vendor
digital models, interface 0x22 and 128 logical words. Earlier profiles and their
evidence remain separate. Unknown source bytes, receipts for another profile and
an altered memory model are rejected.

The normal lint, generic synthesis and RTL harness smoke commands pass. Generic
synthesis contains 3,422 primitive standard-logic cells, 353 state bits and one
real macro black box, with 8,192 physical memory bits reported separately. These
are not physical area or timing measurements. Two exact `always-comb` style
warnings on the unchanged Verilog engine/store are recorded before applying
only that style exception; all other rules and modules pass. All 116 repository
checks pass, including the new source-profile and changed-model controls.

All eleven current SRAM formal stages pass: engine composition/reset, actual
vendor memory induction and observed store mutations, prefetch prediction,
current instruction properties/controls, five support tasks and host deadline.
The new prediction invariant has no design-input assumptions; induction proves
the next registered PC equals the previous prefetch output. A moving-PC cover
passes, and flipping the prediction's low bit produces an inspected mismatch.
The public-readout proof compiles the actual full chip and memory models.

Two preparation failures remain retained. The older fault constructor does not
recognize the new next-state assignment. The explicit, source-pinned
`--engine-style next-state` fixes that constructor without changing RTL or the
property. The second attempt cannot propagate the existing constant BIST tie-off
through the vendor hierarchy during clock analysis. Adding `-flatten` to the
same full-source preparation resolves that constant and the proof passes; no
memory, clock or assertion is replaced.

The complete normal formal command then passes every current SRAM stage but
times out on the first historical engine proof after its unchanged 300-second
wall limit. Its receipt stays `FAILED_OR_INCOMPLETE`; no aggregate PASS exists.
The later semantic audit verifies the successful current results and explicitly
rejects the incomplete combined result. The later [complete normal-command
CI](ci-13660ac/README.md) passes at 13660ac/run43309369604, including the
historical baseline under its original bounds. Its original 1,928-file ZIP,
295 exact inputs, actual producing image, all eight stages and two fresh
116-check executions pass audit and retained Linux replay. Official physical
qualification, production promotion and publication remain required.

`verification.tar.gz` retains 2,154 files, with per-file hashes in `archive.json`.
It includes proof inputs/models/logs/witnesses, the failures and timeout, three
normal fast-stage receipts, runtime observations, and separate original launch
inputs and later audit inputs. The pre-refactor audit driver is reconstructed
only after matching the hash frozen in the actual launch receipt. Compiled
simulator intermediates are omitted; actual source, logs and evidence remain.
Every observed producing container uses immutable image
`sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909`.

Replay from the repository root into a new directory:

```text
python evidence/E0044-sram-current-verification/verify.py --output build/sram-current-replay
```

The replay checks archive membership/hashes, source/model identity, actual
proofs and inspected controls, normal fast-stage receipts, the exact flatten
change, all 116 checks and runtime outcomes. Its success validates this retained
preparation record; it does not turn the historical timeout into a pass.
