# Guarded official run: 36 contact-rule findings, qualification rejected

[Run 43320295442](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43320295442)
at `2be7f5dcc48fb58c42e27645f2ffe14ab751b9a5` completes with 36 Magic findings.
It uses D45's guarded construction and the original Magic rules. It does not
use D46's contact correction. Official precheck and netlist testing are skipped.

Both original ZIPs pass their API size/digest checks. All 1,027 members and 42
frozen producing inputs pass replay; no manifest input is missing this time.
The audit loads the producing definitions rather than current helper code.
The actual checkout, action, support revision, image and physical Yosys
identities are checked against the same job's log.

All final electrical/timing, routed DRC, antenna, power and LVS conditions pass.
The only failed final requirement is `magic__drc_error__count == 0`: the actual
value remains 36. The native circuit comparison matches uniquely, and the
guard passes all 43 public pin rectangles with zero power-clearance violations.
There is no completed submission or official functional netlist result.

The original report contains twelve DigiBnd contact markers and 24 SRAM contact
rectangles. Native measurement resolves these to exactly the same 32 contacts
in the isolated-macro diagnosis: four markers are split into adjacent pieces.
The union of the reported rectangles equals the transformed isolated report
with an empty geometric symmetric difference. Actual Activ enclosure remains
60 nm at the twelve digital contacts and 10 nm at the twenty SRAM contacts.
The limits and their attribution are documented in [D46](../../../docs/decisions/0046-align-magic-contact-rules-with-pinned-references.md).

The official checked GDS and local trial 05 have identical shape geometry on
all 28 layers. Their final functional netlist is byte-identical, SHA256
`2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e`.
This links the diagnostics to the actual failed official run; it does not
convert that run into a pass or waive any report. The complete corrected
Magic run, all official prechecks, submitted-netlist testing, adoption and
publication remain required.

Run `python evidence/E0043-sram-physical-integration/ci-2be7f5d-failure/verify.py
--output build/guarded-failure-replay` from the repository root. Add `--native`
inside the pinned physical image to repeat every measured enclosure, report
footprint comparison and all-layer geometry comparison. Each output must be
new. The original ZIPs, raw reports, source identities and failed status are
preserved unchanged.
