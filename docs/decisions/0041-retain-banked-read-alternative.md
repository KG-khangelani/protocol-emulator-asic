# D41 - Retain the banked read as an alternative, investigate clock routing

Date: 2026-11-12. Status: bounded screen completed; production unchanged.

The sixteen-by-eight-word read network in E0040 preserves D39's exact
clocked store block and all four other modules. Complete-store equivalence
passes in 214.259 seconds, comparing all 4,109 actual state bits and all 54
output bits, with 4,150 comparisons including aliases. The separately
initialized reset proof passes in 17.459 seconds with 134 vector assertions.
No read output is masked and no storage or environment is abstracted.

The real port-driven store test passes on both the parent and candidate in
both simulators: 1,178 checks in Icarus, including two unknown-address cases,
and 1,176 in Verilator. Both reject the deliberate high-bank alias at PC120
after reset and all 512 public store-port writes. This is unit-store coverage,
not the complete chip's external protocol qualification.

The matched whole-chip generic count increases from 15,211 to 15,593 cells
(2.5113%), with the same 4,278 state bits and no latches. A subsequent
[matched mapped screen](../specs/g2-banked-mapped-screen.md) uses the actual
pinned physical runtime, library and synthesis settings. The D39 parent
reproduces its original 34,683 cells / 477,788.2578 square micrometres exactly.
The banked candidate has 32,160 cells / 502,643.5722 square micrometres:
**5.20216% more area**, including 8,233 buffers versus 5,020. Sequential cost
remains identical. Set the banked alternative aside without a routed trial;
its lower mapped cell count does not offset its higher mapped area. The 123-file
archive and replay retain both actual mapped netlists and matched inputs.

Investigate the existing D39 routing failure before choosing the next physical
candidate. The pinned router's edge-usage guard and NDR cost code show that
the failure numbers are weighted routing quantities, not a chip-area margin.
The original post-CTS database has sixteen clock nets with extra spacing;
the router dropped that rule on seven nets before failing. A bounded,
isolated ablation is declared in
[the clock-routing diagnostic](../specs/g2-clock-routing-diagnostic.md).
It preserves all placement and connections while removing those sixteen
assignments on a copy. E0041 retains the first 1,200-second timeout at extra
iteration 40/50, with no final congestion result. One separately declared
2,400-second follow-up is running. This diagnostic cannot qualify a changed
flow. A successful direction still needs a documented physical decision and
fresh complete G2 acceptance with unchanged signoff limits.

The current-source verification profile, original routing failures, G1's
compact10 qualification and separate owner-fluency status remain intact.
