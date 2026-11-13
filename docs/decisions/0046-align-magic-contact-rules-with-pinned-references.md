# D46 - Test alignment of Magic contact rules with the pinned references

Date: 2026-11-13. G2 remains active; no production promotion.

[The retained contact diagnosis](../../evidence/E0043-sram-physical-integration/contact-rules/README.md)
explains all 32 remaining isolated-SRAM Magic markers using actual geometry.
Twelve contacts have 60 nm Activ enclosure inside DigiBnd, where the pinned
foundry document specifies 50 nm. Twenty have 10 nm inside SRAM, where the
pinned KLayout deck specifies 6 nm. Magic instead checks 70 nm and 20 nm.
The foundry PDF's SRAM section is unfinished; the SRAM value is attributed
to the pinned KLayout implementation, not to a nonexistent PDF rule.

Test an explicit local two-file correction. Derive the special regions from
actual GDS marker polygons. Apply the standard 70 nm rule outside both,
50 nm inside DigiBnd outside SRAM, and 6 nm inside SRAM. Preserve the original
70 nm SRAM directional check, other contact types and all other rules. The
5 nm manufacturing grid makes 10 nm the first legal SRAM enclosure that
meets the 6 nm limit; native boundary controls confirm conservative rounding.
Never edit the vendor macro, overwrite the PDK, exclude cells, suppress
reported violations or change the zero-error acceptance threshold.

The entire vendor macro now has zero Magic findings in 450.990 seconds.
All 48 boundary/control cases and the 111-file native replay pass. The
rejected off-grid expectation, failed preparations and failed wrapper are
retained. Hash-check the original reference files before staging and require
the exact two tested output hashes. Reject drift before invoking the checker.

Use a startup wrapper only for `Magic.DRC`, keeping every original Classic
stage and the original full-check script. Temporarily suspend background DRC
while importing the complete GDS, then restore it before the explicit full
check. The separate scheduling diagnostic gets past the import phase where
the original guarded trial has spent over an hour. Its complete result is
still pending, so this is not yet a measured complete-flow speedup.

At the initial checkpoint the helpers were experimental and disabled in the
official workflow. The plan was to complete matched whole-chip diagnostics,
rehearse the portable setup, then qualify a fresh complete flow, every official
precheck and the submitted netlist under the existing 180/45/180-minute limits.
Preserve the original guarded attempts and all failures. Adoption and
publication require the complete G2 audit.

The [portable rehearsal](../../evidence/E0043-sram-physical-integration/aligned-staging/README.md)
now passes in 78.771 seconds, reproduces the exact fixed-pin database and
rejects twelve configurations plus three changed checker/staging inputs.
Its 396-file archive and native replay pass. The optional setup verifies the
entire original Magic source tree, original full-check script and actual
executed helpers before accepting a completed result.

Both initial full-layout diagnostics are incomplete at their declared
1,200-second bounds. A report-parser failure on the empty files obscured their
execution receipts; separate completion reviews preserve that limitation.
Fix reporting before starting separately declared 3,600-second follow-ups.
Do not change the original qualification limits or reinterpret these attempts
as manufacturing passes.

The completed unmodified official run43320295442 now supplies a full-layout
reference: it is rejected with 36 contact markers and all other final physical
conditions passing. The [1,027-file retained audit and native geometry replay](../../evidence/E0043-sram-physical-integration/ci-2be7f5d-failure/README.md)
show that these are exactly the original 32 isolated contact locations, with
four split rectangles. All 28 shape layers match the local diagnostic GDS.
The earlier plan's missing complete original-rule result is therefore present.

Revise the execution order on this evidence: enable the already rehearsed
`--guarded --align-magic` setup for a fresh official run while the bounded
local follow-ups finish. The complete macro check and boundary controls
justify this experiment; only completed fresh checks can qualify it. Keep
the original full DRC script, all 84 stages, every other Magic step and all
zero-error thresholds. Retain original and changed rule identities in the
actual run. Do not extend or relabel the local diagnostic attempts, and do
not promote production before all G2 gates pass.

Both one-hour follow-ups now reach their declared limits after entering full
DRC, without completed reports. Their 17-file replay records actual timeout
receipts. Do not extend them while official run43337581691 is executing the
rehearsed correction from clean source 232ee20 under the original GDS bound.
Native full trial 05 separately completes all 84 original/added stages in
9,381.393 seconds: its 36-finding report is byte-identical to the official
reference, and every other final physical condition matches. The 927-file
completion replay passes. This supplies no corrected full-layout pass and
does not establish a complete-flow speed improvement from import scheduling.
