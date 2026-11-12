# D45 - Correct SRAM import and protect the fixed public pins

Date: 2026-11-13. G2 remains active. No production promotion.

The [first official SRAM run](../../evidence/E0043-sram-physical-integration/ci-2bd2688-failure/README.md)
fails with 58,327 Magic DRC reports and a top-level LVS pin mismatch. Its
original 961-file archive pair, forty frozen source inputs and runtime audit
are retained and replay successfully. An additional JSON-escaping error in
the failing LVS report is preserved; it does not explain away the mismatch.

The actual routed database independently exposes 17 public-pin/power overlaps
and 24 Metal4 clearance violations. Dense macro-aligned power stripes extend
to the die boundary, where they meet the fixed public signal pins. The layout
has exactly 17 fewer nets than the reference. The earlier power-continuity
checks establish connected supplies, not isolation from signal pins.

Remove the standard-cell grid's `-extend_to_boundary` setting so native PDN
generation stops those stripes at the core. Preserve their X coordinates and
widths, the macro grid, existing 144 edge connections and fixed signal pins.
The fresh 38.405-second pilot passes both supply-grid checks. After the original
DEF template creates all 43 public pin rectangles, every pin passes the
independent overlap and 0.42 micrometre Metal4 clearance checks. Native replay
rejects the original database and reproduces the corrected results and both
fresh grid checks. Place the mandatory read-only guard after
`Odb.ApplyDEFTemplate`; the earlier power stage has no physical signal pins.

Also use the seven exact GDS-import patterns from the pinned PDK's
`read_sram_gds.tcl`. The original import gives 232 errors on a real SRAM
subcell; the vendor-prescribed import gives zero using the same full DRC
script and rule deck. An injected small Metal2 shape remains detected.
Both whole-macro 120-second timeouts remain inconclusive. Preserve every
original manufacturing rule and acceptance check.

The [342-file diagnostic archive](../../evidence/E0043-sram-physical-integration/manufacturing-diagnostics/README.md)
retains the failed probes, actual databases, geometry controls and original
decisions. Stop full trials that retain the known shorting geometry. Test the
combined correction in a fresh complete flow with all 80 original Classic
stages, the three existing power/buffer stages and the additional pin guard.
Require fresh routed electrical, DRC, LVS, official precheck and actual-netlist
results before adoption. Correct the official artifact upload to include the
otherwise omitted hidden workflow source. Publish only after the complete G2
acceptance audit.

The [portable guarded staging rehearsal](../../evidence/E0043-sram-physical-integration/guarded-staging/README.md)
now passes in 41.669 seconds and reproduces the exact full-trial fixed-pin
database. Its 369-file archive, source identities and native replay pass;
eight actual bad configurations are rejected. The official workflow uses
this guarded setup and includes the hidden workflow source in its explicit
artifact paths. Full manufacturing, official precheck and actual submitted
netlist results remain required.

A [bounded native LVS diagnostic](../../evidence/E0043-sram-physical-integration/guarded-lvs/README.md)
on trial 05's unchanged routed design now passes in 60.813 seconds. Both
circuits have 4,717 nets and 4,684 devices, and all 45 top-level pins including
supplies match. Illegal overlaps and LVS errors are zero. Its 137-file archive
and corrected native replay pass; the final routed database also passes all
43 public pin checks. Preserve the original native DEF/LEF and black-box macro
scope. Full GDS DRC and the official run at 2be7f5d/run43320295442 remain open.
