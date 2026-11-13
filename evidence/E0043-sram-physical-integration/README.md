# E0043 - SRAM power and physical integration

[D43](../../docs/decisions/0043-qualify-sram-physical-integration.md) and the
[predeclared contract](../../docs/specs/g2-sram-physical-integration.md) retain
the exact five-file SRAM candidate, pinned tools/PDK, 8x4 footprint, 20 ns
target and all existing physical acceptance limits.

The [final netlist completion](ci-232ee20-pin-failure/completion/README.md)
adds all eighteen passing public groups and exact reference records to rejected
run43337581691. Its 477 additional original files replay on Windows/Linux;
the earlier power-port rejection is preserved. Fresh D47 run43348171110 at
94a3082 remains in progress before production adoption and publication.

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

The [first official run is rejected](ci-2bd2688-failure/README.md): 58,327
Magic reports, an actual LVS pin mismatch and a separate JSON-escaping error.
Precheck and netlist jobs are skipped. Both original ZIPs and the 961-file
source/runtime replay are retained. The [manufacturing diagnosis](manufacturing-diagnostics/README.md)
finds 17 real pin/power overlaps and validates native core-bounded stripes
with both power checks and all 43 fixed pins. The pinned vendor SRAM import
also clears the subcell diagnostic while retaining an injected metal error.
The 342-file archive and native database replay pass. D45 requires a fresh
complete flow before any physical acceptance; prior continuity passes did
not establish isolation between public pins and power.

The [portable guarded staging rehearsal](guarded-staging/README.md) passes
in 41.669 seconds and reproduces the exact corrected fixed-pin database.
Its 369-file archive, native replay and eight actual configuration controls
pass. The official workflow now stages this guarded setup; all complete
physical gates remain required.

The [corrected routed LVS diagnostic](guarded-lvs/README.md) passes in
60.813 seconds: 4,717 nets and 4,684 devices match, with all 45 top-level pins
and zero LVS errors/illegal overlaps. The 137-file archive and native replay
pass, including all 43 public pins checked in the finished routed database.
This retains the original DEF/LEF and black-box macro scope; full GDS DRC and
official qualification remain required.

The [local identical-netlist simulator pair](local-netlist/README.md) now
passes all eighteen groups in both simulators, with all 1,052 SPI, 1,160 I2C,
four boundary and 36 abort records identical to the reference. Its 1,145-file
replay passes and retains the diagnosed Verilator reset-alias compatibility
failure and validated adapter. These runs use trial 03's netlist; that layout
is physically rejected and the corrected submitted netlist remains untested.

The [complete KLayout rule-deck diagnostic](guarded-klayout/README.md) passes
on corrected trial 05 GDS in 550.779 seconds. Its native report has 332 rule
categories and zero violations; both retained audits pass. The physical image's
KLayout 0.30.12 result is independent of the complete official precheck and
does not replace Magic DRC or the remaining qualification gates.

The [contact-rule diagnosis](contact-rules/README.md) explains all 32 remaining
isolated-SRAM Magic findings with actual geometry and pinned reference limits.
An explicit two-file correction clears the complete macro; 48 boundary cases
and the 111-file native replay pass, including wrong-reference rejection.
The foundry PDF's SRAM section remains unfinished; its 6 nm value comes from
the pinned KLayout deck. D46's complete-layout diagnostics and fresh official
qualification remain open.

The [optional aligned staging](aligned-staging/README.md) passes its native
78.771-second rehearsal, twelve bad-configuration controls and three changed
input controls. The 396-file archive and native replay reproduce exact pin
geometry and both Magic startup scopes. D46 now enables this setup for fresh
official qualification on the completed original-rule evidence below; the
initial full-layout diagnostics and their one-hour follow-ups are incomplete.
The latter's 17-file replay preserves both timeout receipts without a
manufacturing result. Do not extend these attempts during official qualification.

The [guarded official failure](ci-2be7f5d-failure/README.md) retains run43320295442
at 2be7f5d: 36 Magic contact findings, with every other final physical condition
passing and dependent jobs skipped. Its 1,027 original files and 42 producing
inputs pass replay. Native geometry maps all findings to the same 32 isolated
contact locations and proves identical shape geometry to local trial 05 on
all 28 layers. Full corrected qualification remains required.

The [native guarded completion](guarded-completion/README.md) reaches all 84
stages in 9,381.393 seconds, within the original 10,800-second limit. It has
the same byte-identical 36-finding report and other passing final conditions
as the official reference. Its 927-file report replay passes; the rejected
status remains. Both simulators are now testing the corrected trial 05
netlist in a frozen workspace, separately from manufacturing qualification.

The [aligned official run and pin-precheck rejection](ci-232ee20-pin-failure/README.md)
now retain a complete manufacturing pass at 232ee20: zero full Magic DRC/LVS,
all original electrical/timing limits and exact source/runtime identities.
Independent precheck passes nine checks but rejects exported supply-port spans
with 148 LEF errors. Four unchanged ZIPs retain 1,216 files and 52 producing
inputs; Windows and native Linux replay pass and reject aggregate qualification.
Correct the exported port membership before another complete official run.

The [D47 power-port repair](power-ports/README.md) retains 54 existing full-height
contacts while removing 146 internal port rectangles; every conductor and all
43 signal pins remain unchanged. Native LEF generation, original pin checking,
both grids and exact portable staging pass. The 191-file report/native/checker
replays, four native fault controls, two staging controls and 118 repository
tests pass. The official workflow now enables this additional explicit stage;
complete renewed qualification remains required.
