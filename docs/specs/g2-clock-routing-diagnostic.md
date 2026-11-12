# G2 bounded clock-routing diagnostic

Predeclared 2026-11-12 after D39's GRT-0228 failure and the banked-read screen.
This is a diagnostic ablation on a copy of the failed layout, not a new
qualified physical setup or a change to production inputs.

At the pinned OpenROAD revision dcf36133a369abc8f3c5e5738cd4d82e4903c0e0,
`FastRouteCore::check2DEdgesUsage` bounds edge usage at 100 times capacity.
`Graph2D::getCostNDRAware` adds a 100-times penalty when an NDR net overflows
its layer capacity. These are algorithmic weighted quantities, so 1704/1700
does not quantify a required percentage reduction in chip area.
Sources: [usage guard](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/fastroute/src/utility.cpp),
[NDR cost](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/grt/src/fastroute/src/graph2d.cpp).

The actual post-CTS D39 database contains 16 clock trunk nets assigned
CTS_NDR_0. The fixed flow applied `-apply_ndr half`; the router subsequently
disabled that rule on seven clock nets before failing. This suggests testing
clock spacing as a cause, without assuming that the rule is unnecessary or
that removing it will meet timing or electrical limits.

Use the original run43249867361 post-CTS database. Record its hash and make a
separate copy with only those 16 net-to-NDR assignments removed. Compare DEF
serialization before/after to verify the exact edit; preserve every cell,
location, pin, connection and all other layout data. Keep the same pinned
runtime, PDK, 8x4 footprint, 20 ns clock, routing layers, 30% adjustment and
50 overflow iterations. Run only global routing, with four threads and a
1,200-second wall budget. Preserve every output and timeout/failure.

This ablation intentionally changes clock-route spacing, so it is not an
unchanged-condition qualification or an RTL cost comparison. Even zero global
overflow would establish only a direction to test. Any proposed adoption must
first document the physical change and then pass fresh complete routing,
all-corner timing/electrical limits, antenna/DRC/LVS, precheck and actual-netlist
protocol tests under the approved configuration. No acceptance limit is relaxed.

## One bounded follow-up after the timeout

The first routing attempt reached extra iteration 40/50 and timed out after
1,200.029 seconds. It produced no routed result; preserve it as incomplete.
Its input audit confirms exactly sixteen NDR assignments removed and no
other layout change. The parent mapped-cost replay now reproduces D39's
34,683 cells and 477,788.2578 square micrometres under the installed pinned
runtime and PDK.

Allow one new 2,400-second routing attempt on the identical copied layout,
after both mapped-cost jobs finish. Keep four threads, all 50 iterations,
every routing/physical limit and the exact NDR-only edit unchanged. This
extends only the diagnostic wall budget, not a timing/area acceptance limit.
Retain both attempts and stop this branch if the follow-up is still incomplete
or fails. Any completed route needs a separate overflow/identity audit before
it can motivate a full physical qualification.
