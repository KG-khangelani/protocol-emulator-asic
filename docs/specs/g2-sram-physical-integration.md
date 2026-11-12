# G2 SRAM physical integration contract

Predeclared 2026-11-12 after the passing E0042 complete protocol and mapped
screens. The candidate is the unchanged five-file 0x22 manifest. Production,
G1 and every rejected trial remain separate.

## Fixed physical inputs and model boundary

Keep LibreLane image b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5,
version 3.1.0.dev4, PDK 89d42ee6d2fd9b50b86a1aada6fee6673c3e6008 and the pinned
Tiny Tapeout action/support revisions. Retain the exact 8x4 template, 20 ns
clock, signal routing through Metal4, density/resizer/CTS settings and every
timing/electrical/antenna/DRC/LVS acceptance limit. Do not waive a failure.

Use the actual 256x32 macro's GDS, LEF, CDL and libraries. Its logical capacity
stays 128 words. Remove only `timescale from the derived synthesis black-box
header, since it has no timing behavior. Retain the license and exact ports;
do not change either simulation model or any candidate source.

The three timing model sets are explicit:

| Set | Standard cells | SRAM |
|---|---|---|
| Typical | 1.20 V / 25 C | 1.20 V / 25 C |
| Fast | 1.32 V / -40 C | 1.32 V / -55 C |
| Slow | 1.08 V / 125 C | 1.08 V / 125 C |

The fast set is a mixed-temperature vendor-library evaluation. It does not
demonstrate an isothermal -40 C SRAM condition. Keep the supplied library
values unchanged and expose this boundary in every result. This follows the
available macro interface illustrated by the [SRAM integration example](https://kdp1965.github.io/ihp-um-janestreet-prism/ihp_sram_macro.html),
while retaining this repository's own pinned PDK and acceptance checks.

## First bounded native power-grid trial

Place `store.program_memory` at (20.16, 302.4) micrometres, orientation FS,
inside the unchanged tile. Keep the default 10 micrometre placement halos.
The signal-pin face points into the upper logic region. Its exact LEF supplies
36 VDD columns, 32 corresponding VDDARRAY columns and 36 VSS columns, all on
Metal4. VDD and VDDARRAY connect to VPWR; VSS connects to VGND.

Generate native OpenROAD grid definitions from those actual rectangles. For
each distinct supply-column centre use a 2.1 micrometre stripe, with explicit
net selection and one stripe per declaration. This accommodates the irregular
centre band and the shifted right array. Keep the original 50 micrometre
standard-cell grid pattern outside the macro's x range. Use a matching macro
grid over its boundary, zero PDN halo and skip trimming so matching Metal4
segments can meet at the boundary. These are hypotheses to test in the actual
database, not a claim that power is connected.

Retain the unchanged original LEF obstructions. Keep Magic DRC and illegal
overlap checks enabled; do not copy waivers from other designs. The selected
native options are checked against the pinned OpenROAD command help; newer
options in [upstream documentation](https://openroad.readthedocs.io/en/latest/main/src/pdn/README.html)
are not assumed available.

Bound the first run through OpenROAD.GeneratePDN to 300 seconds. Require
the one correctly placed macro, exactly matched header ports, unchanged
source identity and mapped count, real VPWR/VGND assignment to every macro
supply terminal, and actual same-net overlap with every supply rectangle.
Inspect both grid-check reports and independently check that no power stripe
intersects an opposite-net pin. Preserve the database and exact geometry.
If native generation fails, retain the failure and diagnose before changing
the contract or implementation; do not launch full hardening on that result.

After this pilot passes, run the complete pinned physical flow with fresh
routed metrics, precheck and actual-netlist public tests using the exact macro
digital models. The final checks must identify the same submitted netlist/GDS
and candidate source bytes. The complete current source-verification profile
and publication gates remain required for G2 promotion.

## Native-grid result and bounded edge-connection follow-up

The first native run finishes in 32.640 seconds but fails power acceptance.
The generator removes 72 floating macro stripes; all 104 supply rectangles
lack a same-net routed overlap. The three logical supply terminals have the
correct nets, yet both geometric grid checks fail. Actual external stripes
end at y=301.920 and restart at y=421.660, leaving 0.480 micrometre gaps to
the macro's y=302.400..421.180 boundary. Keep this database and failure.

On an isolated copy of that exact database, try 144 short Metal4 connections:
one at each end of every 36 VPWR and 36 VGND column. Use the existing stripe's
2.1 micrometre width, overlap it by 1 micrometre and extend only 1 micrometre
inside the corresponding power pin. Derive endpoints from the actual database;
reject missing/misaligned wires or gaps larger than 2 micrometres. Add no wire
across the internal VDD/VDDARRAY obstruction band. Preserve every instance,
placement, signal/power net assignment, pin, existing wire and configuration.

Bound this geometry repair and both fresh check_power_grid commands to 120
seconds each. Require an exact wire delta of 144, every one of the 104 supply
rectangles overlapped by its own net, no opposite-net pin overlap, and passing
VPWR/VGND grid checks. Retain the before/after database identities and geometry.
A passing result only establishes this power-grid construction; it does not
qualify routing, timing, DRC/LVS, precheck or the complete physical flow.

## Integrated flow pilot

The isolated edge repair and both grid checks pass. Before full hardening,
run a fresh 300-second pilot through two explicit added stages:
`Project.ConnectSramPower` then `Project.CheckSramPower`, immediately after
`Odb.RemovePDNObstructions`. Keep all 80 pinned Classic stages in their original
order. The first added stage uses the same audited connector and native ODB/DEF
reader/writer; the second runs both actual grid checks and the pinned report
parser. A grid-check error is fatal. The original native grid failure remains
in its own stage; only the fresh successful checks can supply zero violations
to the unchanged later power-grid checker. Freeze and hash the plugin, adapter,
Tcl checker, geometry manifest and resolved configuration with each run.
