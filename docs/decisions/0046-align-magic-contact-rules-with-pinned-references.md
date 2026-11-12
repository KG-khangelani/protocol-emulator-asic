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

The helpers are experimental and are not yet enabled in the official
workflow. First complete the matched whole-chip diagnostics with the original
and corrected rules. Then rehearse the portable setup and qualify a fresh
complete flow, every official precheck and the actual submitted netlist under
the existing 180/45/180-minute limits. Preserve the original guarded attempts
and all failures. Adoption and publication require the complete G2 audit.
