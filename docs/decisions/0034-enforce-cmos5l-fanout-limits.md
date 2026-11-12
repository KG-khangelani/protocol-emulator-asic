# D34 - Enforce CMOS5L fanout limits before physical adoption

Date: 2026-11-12. Status: adopted common correction for requalification;
final official acceptance pending E0031.

## Evidence that requires a revision

D33's complete P and compact10 builds have identical resolved configurations
and timing constraints. Both official GDS jobs and public netlist regressions
pass, but their final reports retain thirty and thirty-seven fanout violations.
P's routed standard-cell area is 13.4968% smaller. That measurement does not
cancel an electrical failure.

The reports impose an eight-load limit. P's violations are clock-tree buffers;
compact10 additionally has a program-store data buffer driving twelve loads.
The default flow uses a general fanout constraint of ten and no explicit
clock sink cluster size. The artifacts, source identities, reports and
netlists remain under E0031/attempts/template-default.

## Shared correction

Apply the same settings to both chips:

| Setting | Original resolved value | Revised value |
|---|---:|---:|
| MAX_FANOUT_CONSTRAINT | 10 | 8 |
| CTS_SINK_CLUSTERING_SIZE | unset | 8 |
| CTS_DISTANCE_BETWEEN_BUFFERS | 0 | 100 micrometres |

The pinned [LibreLane CTS script](https://github.com/librelane/librelane/blob/dcea37e640e792186684004142e51a81a0a554de/librelane/scripts/openroad/cts.tcl)
passes explicit cluster size and buffer distance to OpenROAD. Its
[constraint script](https://github.com/librelane/librelane/blob/dcea37e640e792186684004142e51a81a0a554de/librelane/scripts/base.sdc)
sets the general max-fanout constraint. OpenROAD's
[CTS documentation](https://openroad.readthedocs.io/en/latest/main/src/cts/README.html)
describes an explicit sink count as a hard cluster limit; omitted count
selection is capacitance based. Buffer spacing changes the constructed tree.

A bounded local diagnostic uses the identical pinned image and PDK, exact
E0030 RTL and audited pin DEF. Eight-load clustering alone leaves one clock
root driving sixteen loads in each candidate. Adding the common 100-micrometre
spacing clears fresh nominal-corner fanout, slew and capacitance checks.
The routed diagnostic then passes compact10's electrical checks, but P retains
one data-buffer fanout violation. Detailed-routing database inspection finds
four added antenna diodes on a net with seven functional loads. The first
cluster-only final counts were one/three, not a fully clean result.
The jumper-only trial removes P's fanout violation but leaves two antenna
violations, so it is rejected. Compact10 passes the checked local stages with
normal antenna repair. Retain the three common settings above and normal
antenna protection; stop this local tuning branch. Both official reruns will
retain their outcomes, and compact10 is the fallback if P fails. A smaller
candidate is not adopted merely because it is smaller.

The [diagnostic records](../../evidence/E0031-8x4-physical-comparison/attempts/fanout-diagnostics/result.json)
retain every attempted configuration. The local normal-repair result uses
66,209.3/76,230.2 square micrometres for P/compact10; the remaining P violation
prevents its acceptance. Official requalification remains a separate step.

The 20 ns clock, hold margins, placement density, corner/library set, pin DEF,
die allocation and tool/PDK pins stay fixed. No RTL, program capacity, input
contract or acceptance threshold is relaxed. Update the source configuration,
lock digest, resolved-input checks and comparison contract together.

## Acceptance and evidence

The workflow must reject a nonzero final fanout, capacitance, slew, routing,
antenna, power-grid, Magic or LVS count. It must reject missing/non-finite
results and negative setup/hold at any frozen corner. Retain the failed
review before raising an error. Tests use the actual original failed report
as a negative control; a synthetic copy with cleared fanout supplies only
the checker acceptance fixture.

Preserve each diagnostic's stage and input-state identity. A CTS-only run's
inherited metrics do not establish post-CTS acceptance; use its subsequent
fresh timing report. Local routing without Magic/LVS/precheck/public-netlist
tests is a diagnostic, not official qualification.

Run both revised candidates through fresh complete official workflows and
compare their resulting costs. If either fails, retain the attempt and diagnose
it. G1 adoption and production promotion remain pending their respective gates;
the original 6x4/M0 flow and owner-learning status are unaffected.
