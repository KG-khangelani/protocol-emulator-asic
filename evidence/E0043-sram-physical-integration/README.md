# E0043 - SRAM power and physical integration

[D43](../../docs/decisions/0043-qualify-sram-physical-integration.md) and the
[predeclared contract](../../docs/specs/g2-sram-physical-integration.md) retain
the exact five-file SRAM candidate, pinned tools/PDK, 8x4 footprint, 20 ns
target and all existing physical acceptance limits.

The first native power-grid run completes in 32.640 seconds but fails power
acceptance. All 104 macro supply rectangles have no routed same-net overlap;
the generator removes 72 floating macro stripes and both grid checks fail.
The three supply terminals have correct logical net assignments. Actual
external stripes stop 0.480 micrometres short of the macro boundaries. Command
success is not counted as a pass. The unchanged failed database and reports
are retained.

The separately declared edge-connection trial adds exactly 144 short Metal4
segments to an isolated copy. Every one of the 36 VPWR and 36 VGND columns is
connected at each outer edge. No segment crosses the macro's internal
VDD/VDDARRAY obstruction band. The complete instance/placement/net/pin
identity is unchanged; the exact wire delta is checked. All 104 supply
rectangles have same-net overlap and none has opposite-net overlap. Fresh
OpenROAD checks report all shapes connected on both VPWR and VGND, completing
in 1.073 seconds within the 120-second budget.

Removing the irrelevant timescale from the synthesis-only header clears all
106 earlier lint warnings. The five RTL files and both behavioral models stay
unchanged. The native trial still maps to 4,200 standard cells and one SRAM,
with zero lint errors/warnings, inferred latches or synthesis/check errors.

`power-trials.tar.gz` retains actual before/after databases, exact sources and
settings, native failure logs, geometry, scripts and fresh grid-check results.
`archive.json` binds each member. First extract and validate the archive:

```console
python evidence/E0043-sram-physical-integration/verify.py --output build/sram-power-replay
```

Then run `replay_odb.py --directory /workspace/build/sram-power-replay` through
OpenROAD's Python entry point in the pinned physical image, with this repository
at `/workspace` and the original read-only PDK volume at `/pdk`. It reconstructs
the wire changes from the failed database, requires the exact resulting binary
hash, and reruns both actual grid checks.

The two explicit integrated stages now pass a fresh 31.625-second pilot.
They retain all 80 original Classic stages in order, add the 144 connections
and then run both actual grid checks. Native-stage violations remain recorded;
the fresh checked count is zero. The final database SHA256 is exactly the same
as the separately verified repair. `integrated/` retains the staged plugin,
inputs, stage databases, actual logs/metrics and source/runtime bindings:

```console
python evidence/E0043-sram-physical-integration/integrated/verify.py --output build/sram-integrated-power-replay
```

This qualifies the power-grid construction and its flow integration only. Full
routed timing/electrical checks, DRC/LVS, precheck and actual-netlist protocol
tests remain open. G2 is active and production remains unchanged.

The [electrical trials](electrical/README.md) retain the first two routed
rejections, a failed stricter-target diagnostic and the passing local-buffer
connectivity screen with two checked wiring faults. Both full trials fail nine
extracted SRAM-input slew limits; their later checks were deliberately stopped.
The 1,744-file replay passes. A fresh full buffered run remains in progress.

Its completed extracted timing stage now clears every electrical limit at all
three declared model sets, with positive setup/hold margins and clear routing
DRC/antenna counts. Later manufacturing checks remain pending. The
[portable official staging](official-staging/README.md) reproduces the exact
power database, rejects six configuration faults and passes the 742-file
replay. The separate `gds-sram` workflow carries the exact candidate through
the original official physical, precheck and actual-netlist gates.
