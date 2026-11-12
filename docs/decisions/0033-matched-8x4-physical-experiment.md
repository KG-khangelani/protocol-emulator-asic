# D33 - Qualify the current 8x4 flow with matched complete chips

Date: 2026-11-12. Status: adopted experiment; physical results pending E0031.

The official template at `4b1204ab387b5ab94db1d57067051d8d89a2f83c`
uses the ttihp27a action. Its resolved action commit is
`5e7361fdc445649261c0725dc15f38242dfad330` and CMOS5L default LibreLane
is 3.1.0.dev4. That version and the action's precheck select the same PDK,
`89d42ee6d2fd9b50b86a1aada6fee6673c3e6008`. The support snapshot
`9d13ff3e3e6202090740110438c6a10c1d62ca0f` supplies an 8x4 floorplan.
The existing `src/config.json` matches the current template, so its functional
settings need no change. E0031 retains the audit hashes and source URLs.

Use this reviewed set for G1, with the LibreLane image pinned by digest.
Update metadata and the evaluation contract to 8x4, while keeping 50 MHz and
all shared timing/pin/placement conditions fixed. Preserve the original
M0 lock entry and all historical evidence. A new candidate lock records
pending qualification explicitly.

Run P and compact10 separately through the same official GDS, precheck and
gate-level action. Generate their isolated source copies with the unchanged
E0030 builder; check exact RTL identities before CI stages the selected copy.
Archive a staging manifest so the workflow Git revision cannot be mistaken
for the synthesized source tree. No production RTL promotion occurs.

Reuse the independent public-pin expectations for real-netlist tests and
retain the full SPI alphabet sweep plus negative controls. Validate the
selection first against generated RTL in a harness without the direct engine.
A zero-delay gate simulation and static timing are separate evidence.

The [frozen comparison](../specs/g1-cmos5l-physical-comparison.md) defines the
budgets, required outcomes and decision rule before either candidate runs.
The canary continues to observe the historical M0 qualified ref until the new
flow qualifies; this does not imply the new candidate has passed.

An unsuccessful run is retained and diagnosed. Revise a source, harness or
configuration only for an evidenced reason, then assign a new attempt. Do not
silently change clock, density, input assumptions or acceptance thresholds to
obtain a pass.
