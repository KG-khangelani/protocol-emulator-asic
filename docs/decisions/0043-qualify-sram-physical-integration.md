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
unchanged. Integrate this verified construction as an explicit flow step
before starting full hardening; no physical acceptance gate is relaxed.

G2 stays active until routed/timing, precheck, actual-netlist, integration and
publication gates pass for the same identified candidate.
