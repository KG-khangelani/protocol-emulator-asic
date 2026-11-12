# G2 SRAM complete-chip mapped screen

Declared 2026-11-12 before mapping the SRAM candidate. This is synthesis-only
measurement after the D42 engine/store gates and the complete 30-group pair.
It does not qualify placement, power, routing or timing.

Require the unchanged E0042 five-file candidate and both exact vendor models,
passing compositional engine/reset and real-memory proof/fault controls, and
both full simulator runs with the original 1,052 SPI / 1,160 I2C / four
boundary / 36 abort records and 44-byte bank control. Do not start mapping
while either simulator is incomplete. Retain every preparation/command failure.

Reproduce D39 as the matched reference, using the exact E0040 archived input
configuration, relocated source/template paths and four threads. Use the same
LibreLane image b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5,
PDK 89d42ee6d2fd9b50b86a1aada6fee6673c3e6008, 8x4 footprint, 20 ns constraint,
standard-cell libraries and synthesis settings. Bound each synthesis command
to 300 seconds. Stop at Yosys.Synthesis; do not infer routing from this result.

For the SRAM side, change only the five identified sources and add the actual
256x32 macro views. Derive its black-box port header from the retained vendor
model, preserving the license and every port name, direction and width. Do not
feed the behavioral memory array to synthesis. Include its exact installed LEF,
GDS, CDL and three libraries in MACROS; retain their hashes. The instance path
must be `store.program_memory` in the actual mapped netlist, with exactly one
macro and the public clock on A_CLK. A_DLY remains one; BIST inputs remain zero.

Synthesis uses the 1.20 V / 25 C library. The configuration also declares the
available slow 1.08 V / 125 C library and explicitly associates the vendor
fast 1.32 V / -55 C macro library with the flow's standard-cell fast -40 C
view name. That association is recorded as a mixed-temperature library set;
no isothermal -40 C SRAM characterization or fast timing pass is claimed.
This measurement does not resolve the later physical modeling decision.

Audit actual mapped cell types and connectivity. Report standard-cell count,
state count and area separately from the one 49,488.4992 square-micrometre
macro. Report the sum as complete mapped cell footprint, including wrapper,
valid bits, shadow, engine and all support logic. Do not mistake a flow metric
that omits black-box area for whole-chip cost. Require zero inferred latches,
unmapped cells and synthesis/check errors; retain and explain any lint warning.
The reference must reproduce 34,683 cells / 477,788.2578 square micrometres.

Advance to a separately declared physical integration trial only if the whole
candidate reduces complete mapped cell footprint by at least 20% and all
functional gates remain passing.
Keep every previous failure and the qualified G1 baseline. No production
promotion or publication follows from a mapped saving alone.
