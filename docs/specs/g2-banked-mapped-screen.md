# G2 matched mapped-cost screen for the banked read

Predeclared 2026-11-12 after E0040's generic/proof/port-control results and
before any mapped banked-read measurement. Generic cells increased 2.5113%;
D38 previously showed that generic and CMOS5L mapped savings need not agree.
Use this small mapped comparison to decide whether the alternative merits
the full G2 regression and another physical trial.

Run exactly two complete-chip synthesis jobs, parent D39 and the E0040 banked
read. Use their exact five-file source identities, the original D39 merged
configuration, the pinned LibreLane image and CMOS5L PDK, and four OpenROAD
threads. Relocate only filesystem paths. Stop at Yosys.Synthesis, with a
300-second budget per job; do not start while the bounded clock-routing
diagnostic is still consuming its budget. Retain logs, generated mapping
script, resolved configuration, library/source identities and actual netlists.

Require successful mapping with no latches, no unmapped cells and all 4,278
sequential cells present. The parent must reproduce the original 34,683
mapped cells and 477,788.2578 square micrometres before calling this a matched
comparison. If it differs, investigate and retain that discrepancy. Compare
total area, sequential area and combinational cell types; do not infer timing,
placement locality, routing feasibility or a routed saving from these numbers.

This does not adopt either implementation or alter production/configuration
files. Both the RTL and any proposed clock-routing change remain subject to
the full G2 gates before promotion or publication.
