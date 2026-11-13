# D47: existing full-height supply ports

The exact 232ee20 submitted database contains 200 power-port rectangles.
Native selection removes 146 internal BPin rectangles and retains 27 existing
full-height straps per supply. Every conductor, connection, instance and public
signal pin remains unchanged: native DEF bytes outside the PINS section and
all 43 signal-pin entries are identical. Both power grids pass fresh checks.

The original Magic LEF generator completes in 123.026 seconds. The unchanged
pinned Tiny Tapeout pin checker reproduces the original **148 LEF errors** and
passes the selected-port LEF against the exact submitted GDS. Native selection
takes 3.831 seconds, public-pin clearance 2.127 seconds and fresh grid checks
80.228 seconds, within the declared bounds. Two setup failures remain retained.

Portable `SramPortsClassic` staging reproduces the exact selected database in
9.402 seconds. It adds one stage after `Odb.CellFrequencyTables`; all original
80 stages and the four earlier additions remain in order. Its two staging
corruption controls pass. Four native malformed-port controls (wrong width,
wrong layer, absent conductor and missing full-height straps) are rejected
before changing the input database. Doctor and all 118 repository tests pass.

`diagnostic.tar.gz` retains 191 files. The index identifies 62 omitted generated
views; original ODB/GDS remain in the unchanged official ZIPs beside this
directory. Native replay regenerates the selected ODB and checks its exact hash
`77bb30a71ccc0ea6c0fc2f32fa4f724ea702b03266a0f53fddc71a09beb413e1`.
Reports, native replay and replay of both original/selected pin checks pass.
Actual retained container receipts bind the pinned images and read-only PDK.

Run `verify.py --output build/<new-directory>` for report and file checks.
In the pinned physical image add `--native`. In the pinned workbench add
`--pins --dependency-dir <directory>` with exactly gdstk 0.9.52 and NumPy 1.26.4,
matching the pinned precheck requirements. The checker source itself is frozen
inside the archive. These are bounded repair diagnostics. Fresh complete
manufacturing, all ten prechecks and actual-netlist qualification remain
required; the original official pin failure is not reclassified as a pass.
