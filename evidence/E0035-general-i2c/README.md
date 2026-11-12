# E0035 - Complete I2C using general instructions and measured real storage

Date: 2026-11-12. Decision: D37. **Experimental protocol progress; G2 remains
active. Production and physical configuration are unchanged.**

The complete programs use a general WAIT_PIN failure destination, an eight-bit
PC and real banked program memory. `od128` additionally offers open-drain TX
and initial alternate-payload selection on existing manual/phase shifting.
There is no I2C-specific operation or hardware controller. D36's independent
oracle is unchanged, and the external target sees public pin events only.

| Measurement | compact10 reference | literal255 | od128 |
|---|---:|---:|---:|
| Allocated program words | 10 | 255 | 128 |
| Program bits | 320 | 8,160 | 4,096 |
| Complete write / read / combined words | Does not fit | 136 / 93 / 211 | 54 / 53 / 96 |
| Current whole-chip generic primitive cells | 3,589 | 51,723 | 27,065 |
| Current whole-chip state bits | 477 | 8,343 | 4,278 |

The current generic synthesis includes actual program storage, loader, data
registers, synchronizer and executor. These counts are not CMOS5L mapped area,
timing or physical feasibility measurements. D37 advances od128 for those
remaining gates; it does not claim a minimum instruction set or minimum store.

## What passed and which source it measures

`full-od128/` contains 1,160 identical records per simulator on the frozen
pre-cleanup candidate: 768 nominal transactions, six NACK locations, 76 stretch
positions, 304 deadline cases and six required rejections. Accepted outcomes
include OK, NACK and TIMEOUT. The six bad-program/input controls must be rejected.
All 256 byte values and ordinary addresses are represented. Four response
offsets cover the four core phases, with one assigned offset per byte; this is
not a full parameter cross product. Nominal rates are about 98.4--98.6 kHz,
below the frozen 100 kHz ceiling. Every exact observed rate is retained.

`combined/` qualifies twelve existing public groups on that same frozen RTL
in both simulators: reload, input wait, loop, shift, UART TX, bounded UART RX,
and all four SPI modes/both orders. The 1,052 SPI records are identical between
simulators and equal the retained compact10 baseline: 1,048 accepted transfers
and four expected input-hold failures. UART host-service/framing/delivery limits
and SPI held-input assumptions remain. Continuous autonomous receive delivery
and broader SPI input compatibility are not established.

`sources/pre-cleanup/` and `sources/current/` retain exact generated files.
`cleanup-equivalence/` proves both old/current engines functionally equivalent;
top connections differ only in whitespace, data/synchronizer files are identical,
and a separate theorem covers all 256 length values for the literal store's
constant-check cleanup. This bridge makes the historical test evidence usable
without pretending its source hashes were the current hashes. A new CI workflow
also reruns the complete matrices at the committed revision.

The current od128 32-case I2C smoke passes both simulators. The corrected literal
smoke also passes both; it and the instruction-proof sources differ from current
only in whitespace. The literal full Icarus matrix passes all 1,160 cases, but
the original full Verilator launch failed on a redundant constant comparison
before simulation. That full corrected second-simulator gate is still pending CI.

`boundaries/` passes four groups for each candidate and simulator. It checks
all 256 bank/length inputs, every allocated byte lane, reset, no aliasing through
the unallocated final literal word, full PC visibility, high/invalid destinations,
immediate/delayed legacy-skip overflow, partial-byte/loop abandonment, enable
freeze and serial-option behavior. The od128 serial sweep has 160 public cases.

`instruction/` passes induction and reachable covers for both engines. Two
deliberately wrong engines fail with inspected witnesses: one retains an active
loop after branching; the other actively drives a released open-drain one high.
Assertions also require the eighth capture for a completed receive write,
the correct sampled result, and no completed write on an abort branch.

`aborts/` qualifies the current od128 in both simulators: 18 explicit reset,
disable or isolated-loader interventions at six transaction positions, each
followed by a fresh successful public reload/read without another chip reset.
The 36 records and full-trace hashes agree. Loader-owned raw values are read
through the public loader registers while the target is isolated. An abort is
never counted as a successful I2C transaction.

## Retained failures and limits

- The expanded PC exposed an actual wraparound bug: legacy skip at word 254
  reached word zero. The counterexample is retained; immediate and delayed
  overflow now fault at the original address.
- Early launch flags replaced simulator defaults, a shell filter lacked quotes,
  and the combined-result parser initially treated intentionally excluded test
  discoveries as failures. These unsuccessful attempts remain. The corrected
  parser requires all twelve selected tests and only the exact allowed skipped
  discoveries; its reused Icarus simulation has verified unchanged test/RTL inputs.
- A boundary recorder counted interim failure witnesses as additional successful
  groups; the corrected recorder writes that witness only on a real failure.
  Current groups pass. Generated RTL lint failures were corrected and the final
  candidate passes Verible; the hardware cleanup is proved equivalent.
- The symbolic arbitrary-word store proof times out at 240 seconds for both
  capacities. Reachable covers pass, but this does not close the unbounded store
  proof. Alternative proof attempts remain separate, explicitly scoped records.

There is no fresh mapped/routed result, timing/fanout/precheck qualification or
real-netlist protocol result for this candidate. G1's physical qualification,
P rejection, old 6x4 results and pending owner fluency are preserved. No G2
production promotion, completed goal or newly qualified release is claimed.

## Reproduce

In the locked workbench, use new output directories:

```sh
python3 experiments/i2c/run_general_gate.py --gate od128 --output build/g2/new-od
python3 experiments/i2c/run_general_gate.py --gate literal255 --output build/g2/new-literal
python3 experiments/i2c/run_general_gate.py --gate architecture --output build/g2/new-architecture
```

The architecture gate checks boundaries, abort/reload, scoped instruction
proofs, whole-chip generic cost and the existing public UART/SPI matrix. It
does not silently include the inconclusive store proof as a pass. Source hashes,
commands, statuses, JUnit, all case records and selected full witnesses are
retained here; bulk simulation/proof/netlist intermediates remain under `build/`.
`SHA256SUMS` covers every curated artifact, including compressed byte-exact logs.
