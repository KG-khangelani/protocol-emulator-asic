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

The full eighteen-group public selection is currently running in both
simulators. Its independent expectations, 1,052 SPI records, 1,160 I2C records,
four architecture summaries and 36 abort/recovery records remain unchanged.
Physical staging rejects this revision until the complete local qualification
record exists. Clean CI adds separate store and public-selection gates.

The earlier E0036 screen measured 24,391 versus 27,065 generic cells with
4,278 state bits unchanged, and complete od128 store equivalence passed.
This is not a mapped/routed saving. The next physical trial keeps D34's pinned
8x4 conditions, every physical limit, all ten prechecks and all eighteen actual
netlist test groups. G1's qualification and owner-fluency boundary are preserved.
