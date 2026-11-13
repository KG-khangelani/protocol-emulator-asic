# D47 - Export the existing full-height supply straps

Date: 2026-11-13. Status: **bounded repair passes; complete qualification pending**.

The corrected 232ee20 build passes complete manufacturing checks, but the
unchanged official precheck rejects 148 supply-port LEF conditions. Each
exported supply rectangle must be Metal4, at least 2.1 micrometres wide and
within 10 micrometres of both vertical edges. Its pinned source is
`TinyTapeout/tt-support-tools@9d13ff3e3e6202090740110438c6a10c1d62ca0f`,
`precheck/pin_check.py` (blob `8b6761891a23a29310ceb7b2c078819fce4934be`).
The [original archive replay](../../evidence/E0043-sram-physical-integration/ci-232ee20-pin-failure/README.md)
preserves the failure, passing manufacturing checks and nine other prechecks.

Native PDN generation exports fragmented internal straps around the SRAM and
the template's supply connection as external ports. The routed database has
100 rectangles per supply. Of these, 73 per supply do not span the chip.
The ordinary full-height straps already provide 27 valid contacts per supply.

Select those existing contacts after `Odb.CellFrequencyTables`, before RC
extraction and signoff. Remove only the 146 internal power BPin rectangles;
keep 54 existing full-height rectangles and both supply terminals. Require
all port rectangles to lie inside the die, have the correct layer/width and
be covered by real same-net supply conductors. Reject unexpected counts or
missing conductors before editing. Keep every power wire, via, instance,
connection and public signal pin. Require native DEF bytes outside the PINS
section and every public signal-pin entry to remain identical.

This adds one explicit `Project.SelectSramPowerPorts` stage in
`SramPortsClassic`: 85 stages, with all original 80 in order and D43-D46's four
existing additions. It changes no RTL, macro, placement, routing, rule or
acceptance threshold. Keep the original LEF generator and every precheck.

The bounded native probe on the exact submitted database passes selection,
original Magic LEF generation, all 43 public-pin clearance checks and both
fresh supply-grid checks. The unchanged pinned pin checker reproduces all
148 original errors and passes the regenerated LEF against the exact submitted
GDS. Two preparation errors are retained separately. The wire/placement DEF
content is byte-identical before and after. These diagnostics justify the
portable repair; a fresh complete official build, precheck and actual-netlist
qualification remain required before production promotion.

The [191-file retained diagnostic](../../evidence/E0043-sram-physical-integration/power-ports/README.md)
passes report, native-selection and original-checker replay. Four native
port mutations are rejected before partial edits, and two staging controls
detect removed selection and an altered contract. Portable staging reproduces
the exact selected database in 9.402 seconds. Doctor and 118 repository checks
pass. Enable this tested optional setup in both official staging steps, retaining
the selector and native wrapper; follow with a new complete qualification run.
