# E0038 - Shared program-word read qualification

D39 advances the exact E0037 shared-read screen as `od128-shared`.
All five source files and the manifest are frozen under `sources/`.
The store SHA256 is
`d844a1eed97a72bda57edc3344a97020202fef5539a4782945c18bc7551384bf`.
All four other modules are byte-identical to D38; capacity stays 128 words,
ISA remains 0x21, and no clock, latency or protocol-specific path is added.

The original E0037 screen retains 15,211 versus 24,391 generic cells, conditional
store equivalence and reset-reachable complete-chip equivalence. These are
not physical measurements. D38's independent physical run remains in progress.

Fresh local checks:

- Both simulators pass the baseline and observe all three deliberate faults:
  high-bank read aliasing, execution stuck on the loader's address, and missing
  length readback. Retained observations include all 512 byte writes and reads,
  the length/ready result and six public execution edges, seed 20261112.
- Scoped style passes under D39's explicit inherited exceptions. The initial
  failure caused by the displaced line waiver remains retained.
- Fresh complete-chip temporal equivalence and the reset base pass: all 4,278
  actual state bits and 24 public output bits are covered, with 4,572 proven
  bit comparisons including aliases and 217 vector reset assertions. Temporal
  induction closes at one step; reset starts the two chips independently.
- All eighteen public groups pass in both simulators: 595.887 seconds Icarus
  and 392.544 seconds Verilator. Each reproduces all 1,052 SPI, 1,160 I2C,
  four boundary and 36 abort/reload records from the audited reference.
- Ten corrupted proof/witness cases are rejected, including missing actual
  state/output coverage, an unproven bit, a disabled reset assertion, changed
  reset premise, missing success log and wrong public counterexamples. Model,
  observation and source hashes are updated in the controls so semantic checks
  must reject the corruption. Candidate production/physical status stays open.

`qualification.json` reports **PASS_SHARED_CANDIDATE_RTL_FORMAL**. The retained
replay verifies all 1,030 archived files and reproduces the ten audit controls.
Physical staging preflight passes; its retained inputs are explicitly marked
as local, not a completed or in-place CI physical run.

`archives.json` binds every retained member and each original compressed
archive. Reproduce the two CI gates in the locked workbench using
`experiments/i2c/run_general_gate.py --gate shared-selection` and
`--gate shared-proof-controls`, each with a new `--output build/...` directory.
Replay retained evidence using `python evidence/E0038-shared-program-read/verify.py
--output build/new-replay-directory`.
Physical qualification, production integration and publication remain pending.
