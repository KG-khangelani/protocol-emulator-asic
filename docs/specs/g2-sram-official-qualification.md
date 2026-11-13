# G2 SRAM official qualification

This is the official-workflow continuation of D42/E0042 and D43-D46/E0043.
The isolated five-file `od128-sram` candidate remains interface 0x22 and has
128 logical words. Production promotion is a later decision. The physical
construction is specified in [the integration contract](g2-sram-physical-integration.md).

Use the original pinned 8x4 action, support revision, LibreLane image and PDK.
Stage the exact audited candidate only inside a clean CI checkout. Generate
portable macro paths to the actual pinned GDS, LEF, CDL and three Liberty
files; identify their bytes against the retained matched-mapping inputs.
The fast model set combines standard cells at -40 C and vendor SRAM at -55 C.
It does not characterize the SRAM isothermally at -40 C.

Keep every original Classic stage in order. Add the two verified power
stages, the nine native input buffers with fatal connectivity audit, and the
read-only public-pin/power guard after `Odb.ApplyDEFTemplate`. D45's guarded
flow has 84 stages: all original 80 and those four project stages. Keep
all original limits, the unchanged tile and clock, Magic DRC, illegal-overlap
checks and LVS. The rejected 0.4 ns diagnostic and extra generic post-routing
repair setting are absent. The workflow retains exact staged sources, plugin,
generated power geometry, portable configuration and verification inputs.
Include hidden files within these explicit artifact paths so the actual
workflow source under `inputs/.github/` is retained.

Use native core-bounded standard-cell-grid stripes; the earlier die-boundary
extension shorts 17 fixed public pins. Preserve the macro stripes and 144
edge bridges. After the fixed DEF template places all 43 public pin rectangles,
require no same-layer overlap with power conductors and at least 0.42
micrometres of Metal4 clearance. The guard must inspect the actual unchanged
database and fail on a violation. It supplements the original full DRC/LVS.
Use exactly the seven GDS import patterns in the pinned PDK's
`read_sram_gds.tcl`, SHA256
`5a818473a3ffad96d84e1f72331fbb94c46cc1df24a01bc9d8367ac3a7211cd7`.
No DRC rule, checker or macro geometry is waived or changed by this import.

D46 explicitly aligns only the low-voltage contact-enclosure implementation
with its pinned references: 70 nm outside special regions, 50 nm inside
DigiBnd outside SRAM, and 6 nm inside SRAM. The original 70 nm directional
SRAM check and all other rules remain. The 5 nm manufacturing grid makes
10 nm the first legal SRAM enclosure meeting the latter limit. Attribute
50 nm to the pinned foundry document and 6 nm to the pinned KLayout deck;
the PDF's SRAM section is unfinished. Derive coverage from actual marker
polygons and require the exact two tested technology-file hashes. The
reference identities and output hashes are fixed in `align_sram_magic.py`.

Stage this as `--guarded --align-magic`. Keep the pinned PDK unchanged and
reject changes to its complete 35-file Magic tree, six reference files or
the original full DRC script. Only the `Magic.DRC` startup uses the local
copy. Suspend background DRC during GDS import and restore it immediately
afterwards, including on import error; execute the original complete
synchronous rule check and unmodified report/count handling. Other Magic
steps keep their original setup. Retain the actual executed startup/helper,
original full script, copied rule files and alignment receipt; verify these
against the staged manifest before accepting final results. No cell is
excluded, no report is filtered, and the required final count remains zero.

Require all final physical counts to be zero, finite nonnegative setup/hold
at all three declared model sets, and no slew/capacitance/fanout violations.
The power and buffer receipts must bind the actual databases consumed and
written by their stages. The submitted netlist must equal the final physical
netlist and contain one real SRAM instance. Follow with all ten original
official prechecks and all eighteen public test groups on that same submitted
netlist, using both unmodified vendor SRAM digital models. Retain the complete
1,052 SPI, 1,160 I2C, four boundary and 36 abort observation sets and compare
them against the previously audited reference records.

Bound GDS to 180 minutes, precheck to 45 minutes and public netlist testing to
180 minutes. A failed or incomplete stage remains a failure or incomplete
result. Download and verify the original workflow archives, source/runtime
identities and consumed submission digests before claiming qualification.
Current production-profile integration and publication remain separate G2 gates.

D47 adds optional `--power-ports`, requiring both guarded and aligned setup.
`SramPortsClassic` has 85 stages: the same 84 plus supply-port selection after
`Odb.CellFrequencyTables`. Select 54 existing full-height Metal4 power-port
rectangles from the original 200; remove only the other 146 BPin rectangles.
Require the actual conductor to cover every original rectangle, at least
2.1 micrometres width, in-die bounds, and 27 retained rectangles per supply
within 10 micrometres of both vertical die edges. Reject unexpected geometry
before editing. Preserve all non-pin DEF bytes and each public signal pin.
Bind both actual stage DEFs and the input database to the selection receipt.
Keep the native LEF generator, complete manufacturing rules and all ten
prechecks, including the previously failed pin check.
