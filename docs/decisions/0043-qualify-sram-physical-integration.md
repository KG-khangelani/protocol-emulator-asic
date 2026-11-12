# D43 - Qualify the SRAM candidate's physical integration

Date: 2026-11-12. Status: native power trial fails; bounded edge connections
pass geometry and both power-grid checks. Full physical acceptance and
production promotion remain open.

D42/E0042 passes the complete protocol pair and relevant proof/fault controls.
Matched pinned mapping reduces complete cell footprint by 78.5306%, including
one actual SRAM. This clears the predeclared screen and justifies a fresh
physical integration trial under the [new explicit contract](../specs/g2-sram-physical-integration.md).

Keep the exact five candidate source files, 8x4 boundary, 20 ns target, pinned
tools/PDK and every existing timing, electrical, antenna, DRC and LVS acceptance
limit. Add the required macro views, placement and power connections. Remove
only the synthesis black-box header's irrelevant timescale directive; preserve
the vendor behavioral models used by simulation.

First run a bounded native power-grid/floorplan trial. Derive individual Metal4
power stripes from the actual macro LEF instead of assuming its columns have
uniform spacing. Audit resulting geometry and connectivity before a full
hardening run. Preserve unsuccessful trials; do not turn tool warnings or
unconnected supplies into a pass.

The fast model set explicitly combines standard cells at 1.32 V / -40 C with
the supplied SRAM library at 1.32 V / -55 C. This is the available vendor model
set, not an isothermal -40 C SRAM characterization. Typical and slow libraries
match their respective temperatures. Any timing qualification must state this
boundary and retain all actual library hashes. No library values are edited.

E0043 retains the native failure: all 104 supply rectangles are unpowered,
despite correct logical assignments, because external stripes stop 0.480
micrometres short. The separately declared follow-up adds 144 short outer-edge
connections and passes all rectangle/net checks and both fresh grid checks.
The 260-file replay reconstructs the exact after-database binary hash and
reruns both passing checks. Candidate source, placement and signal nets stay
unchanged. The two explicit added steps now pass a fresh 31.625-second pilot
and reproduce the exact repaired database. All 80 original Classic steps stay
in order and the later power checker consumes fresh checked metrics. The
first full run clears routing but fails nine extracted SRAM-input slew limits.
Enabling the existing post-route repair changes no cells and leaves the same
failure. Both rejected runs are retained; their remaining manufacturing checks
were stopped after that decisive result. The 0.4 ns diagnostic also fails its
stricter target and is not adopted.

A separately declared local-buffer screen adds nine native buf_4 cells at the
affected SRAM inputs and reports zero fresh typical estimated slew violations.
The actual database audit recovers all original connectivity after collapsing
those buffers and rejects two deliberately rewired databases. All 1,744 retained
files and the actual database/negative-control replay pass. A fresh third full
run now tests this narrower physical change under the original limits; no
physical acceptance gate is relaxed. See [the electrical trials](../../evidence/E0043-sram-physical-integration/electrical/README.md).

The third run clears all extracted electrical limits with positive setup/hold
margins at all three declared model sets; routing DRC and antenna counts are
zero. Its manufacturing checks remain in progress. The portable official
staging rehearsal reproduces the exact repaired power database in 39.324
seconds and rejects six deliberately corrupted resolved configurations. All
114 repository checks and the 742-file replay pass. Advance this exact source
to the separate pinned `gds-sram` workflow, retaining all original acceptance
checks. See [the official qualification contract](../specs/g2-sram-official-qualification.md)
and [staging evidence](../../evidence/E0043-sram-physical-integration/official-staging/README.md).

G2 stays active until routed/timing, precheck, actual-netlist, integration and
publication gates pass for the same identified candidate.
