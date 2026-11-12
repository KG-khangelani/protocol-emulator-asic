# G2 SRAM official qualification

This is the official-workflow continuation of D42/E0042 and D43/E0043.
The isolated five-file `od128-sram` candidate remains interface 0x22 and has
128 logical words. Production promotion is a later decision. The physical
construction is specified in [the integration contract](g2-sram-physical-integration.md).

Use the original pinned 8x4 action, support revision, LibreLane image and PDK.
Stage the exact audited candidate only inside a clean CI checkout. Generate
portable macro paths to the actual pinned GDS, LEF, CDL and three Liberty
files; identify their bytes against the retained matched-mapping inputs.
The fast model set combines standard cells at -40 C and vendor SRAM at -55 C.
It does not characterize the SRAM isothermally at -40 C.

Keep every original Classic stage in order. Add only the two verified power
stages and the nine native input buffers with fatal connectivity audit. Keep
all original limits, the unchanged tile and clock, Magic DRC, illegal-overlap
checks and LVS. The rejected 0.4 ns diagnostic and extra generic post-routing
repair setting are absent. The workflow retains exact staged sources, plugin,
generated power geometry, portable configuration and verification inputs.

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
