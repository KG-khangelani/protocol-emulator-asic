# D38 - Qualify explicit byte writes after G2 routing failure

Date: 2026-11-12. Status: bounded candidate trial; production unchanged.

E0036 rejects the original physical candidates under D34's unchanged 8x4 flow.
literal255 exceeds placement capacity. od128 maps to 39,806 cells and
564,744.3984 square micrometres, then fails global routing with GRT-0228
congestion. Its skipped precheck and netlist jobs are not passes.

Try the od128 byte-write simplification already measured in E0036. Replace
each variable eight-bit write part-select with a four-way byte-lane case using
constant bit ranges. Preserve all 128 words, reset, readback, bank controls,
length validity, fetch timing and interface. The other four chip modules and
all protocol programs remain byte-identical. This adds no instruction and no
protocol-specific circuit. Keep the original generator and E0035 source frozen.

The prior screen reduced generic cells from 27,065 to 24,391 with 4,278 state
bits unchanged. Complete od128 store equivalence and the local byte-update
theorem passed; the wrong-lane control differed as expected. These results
justify a physical trial, not a mapped/routed saving. The literal equivalence
timeout remains inconclusive and literal255 is not revised by this decision.

Before the next physical run, require all 652 actual-store assertions with
unbounded induction, cover witnesses and reset-reachable alias/lane controls
on the exact revised source. Require the unchanged eighteen public test groups
in both simulators and exact E0036 protocol/boundary/abort records. Preserve
proof models, witnesses, logs, source hashes and failed attempts in E0037.
Retain the prior instruction proofs for the byte-identical engine and the
complete-store equivalence link; do not claim arbitrary-firmware correctness.

Use `od128-lanes` to identify this implementation separately from E0035 od128.
Its software-visible identity remains 0x21 because observable semantics do not
change. Run the same pinned physical workflow with the same die, clock,
density, corners, fanout, antenna limits, prechecks and actual-netlist selection.
If it fails, retain the failure and inspect the new cost/congestion before
choosing another change. No physical threshold is relaxed.

G2 remains active through complete physical qualification, production
integration and verified publication. G1 and the separate owner-fluency status
remain as recorded.

The existing screen's byte cases enumerate all four binary selector values,
so an omitted default means hold only for unknown simulation inputs. Verible
reports 128 `case-missing-default` style warnings. Preserve those observations
and waive that one style rule only for the frozen generated program store.
`lint_store_lanes.py` first checks every case's four exact labels and ranges,
requires exactly those 128 unwaived warnings, then checks all other rules and
the other four modules normally. This documented style exception preserves
the tested source; it changes no functional property or physical limit.
