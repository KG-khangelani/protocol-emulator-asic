# E0037 - Explicit byte writes after od128 routing failure

D38 qualifies a separate `od128-lanes` implementation. It reproduces E0036's
screened rewrite byte for byte: each word uses four constant byte-write ranges.
All other module bytes, 128-word capacity, interface, instructions and protocol
programs remain unchanged. Original E0035 sources and both physical failures
remain frozen. Production is unchanged and G2 remains active.

The exact new store passes all **652 assertions** with unbounded induction:
32 read/transition partitions and one three-target cover task. No actual
program bits are initialized or environment/reset constraints assumed in the
positive proofs. All storage/control logic remains in every partition.
The alias and wrong-byte-lane mutations produce inspected reset-reachable
wrong writes. All nine corrupted proof-summary controls are rejected.

`store.tar.gz` and `archives.json` retain exact generated sources, proof models,
task configurations, successful induction logs, status files and witnesses.
The independent auditor reconstructs the asserted source and mutations from
the frozen candidate. Original E0035 store audits still replay unchanged.

The full **eighteen-group public selection passes both simulators**. Each
reproduces all 1,052 SPI records, 1,160 I2C records, four architecture summaries
and 36 abort/recovery records exactly. UART framing/service bounds and the SPI
held-input successes/edge-only controls remain unchanged. The independent
retained-evidence replay verifies 1,123 archived files and every required proof,
record set and test identity. [Qualification](qualification.json) identifies
the exact candidate. All seven e5eef5b CI jobs pass. The [new-candidate archive
audit](ci/e5/verification.json) verifies both original D38 ZIPs, source bytes,
all 652 assertions, inspected controls and the full public records in both
simulators. Both original ZIPs are retained. The other five successes are
observed from GitHub; their current archives are not re-audited in this record.
Later style-review and fresh-checkout-test-fix checks remain separate.

Reproduce the archive/evidence audit without rerunning the solvers/simulators:

```sh
python evidence/E0037-explicit-store-lanes/verify.py --output build/g2-lanes-replay
```

The unwaived lint report contains 128 `case-missing-default` style warnings.
D38 documents one exception for this exact generated store. A dedicated check
requires all four labels and bit ranges for every two-bit byte selector,
exactly those 128 warnings, and clean results for every other rule/module.
Original and scoped logs are retained in `style/`; no RTL or physical limit
was changed to obtain the scoped result.

The standard 869ee34 CI failed because the first archive unit test assumed
`build/` existed. The fix creates that test output parent. All 106 checks pass
in a fresh committed snapshot with only that fix and no prior build directory;
[failure/fix evidence](ci/clean-check-fix.json) retains the original failure.
It changes no chip source or physical input. The replacement CI is pending.

The physical trial is [run43241097269](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43241097269)
at 869ee34. Candidate staging passes; final physical evidence is still pending.

The earlier E0036 screen measured 24,391 versus 27,065 generic cells with
4,278 state bits unchanged, and complete od128 store equivalence passed.
This is not a mapped/routed saving. The next physical trial keeps D34's pinned
8x4 conditions, every physical limit, all ten prechecks and all eighteen actual
netlist test groups. G1's qualification and owner-fluency boundary are preserved.

## Separate bounded shared-read screen

The top's loading/execution ownership suggests sharing the program memory's
read network. The [predeclared screen](../../docs/specs/g2-shared-read-screen.md)
selects the loader address or PC before a single word read and selects the
loader byte afterward. All 4,278 state bits and all write/control behavior stay.

[Screen evidence](shared-read-screen/verification.json) measures **15,211 versus
24,391 generic cells**, a 37.636833% reduction from D38. Sequential equivalence
passes when comparing each read output only in its active mode, with other
outputs compared normally from corresponding state. Raw inactive read outputs
deliberately differ. Top-level ownership is a source-derived premise; this is
not full-chip equivalence, public regression or physical qualification.

Two initial generator assertions stopped before synthesis and are retained.
The corrected experiment preserves length readback and selects the byte after
evaluating the shared word. This promising alternative is not adopted, and
does not replace D38's exact candidate or current physical trial.

The subsequent [complete-chip proof](shared-read-screen/chip-equivalence/verification.json)
passes with **all 4,278 actual state bits and all 24 public output bits**
compared. Every one of 4,572 bit comparisons, including aliases, is proven;
only combinational internal match points are excluded. The temporal proof
closes at induction step one. An independent SAT base starts both chips with
unconstrained independent state and proves correspondence after a sampled
reset edge, for arbitrary defined digital public inputs.

This extends the conditional unit result to reset-reachable public behavior
of the complete digital chip. It is not new public simulator coverage, an
adversarial mutation check or physical qualification. The initial reset-result
collector confused vector assertion count with bit count; the corrected run
checks all 217 vector assertions / 4,572 bits. A separate four-step base times
out at 90.064 seconds and remains inconclusive; the completed one-step
induction needs only the successful one-step reset base. All inputs/models,
logs, scripts and failed attempts remain retained.
