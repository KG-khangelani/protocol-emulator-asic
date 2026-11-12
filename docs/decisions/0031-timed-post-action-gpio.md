# D31 - Select timed post-action GPIO for the next mapped experiment

Date: 2026-11-12. Status: local and clean-CI qualification complete at19265ff/run43148870589;
publication is tracked in E0030. Production and historical compact sources remain unchanged.

P fits the explicit-idle mode1/3 transfer into eight words while preserving the
matched ten-word design's pin/direction/receive/terminal timing. It uses 3,146
generic complete-chip cells and 412 state bits, versus3,589/477 for compact10.
The reduction is 443 cells and 65 bits. Relative to compact8, only 39 cells
are added; the same wait counter carries SET and DRIVE post-delays.

F also fits eight words, but costs 3,228 cells/429 bits
and its local compact refinement remains inconclusive at 180s. Clean CI qualifies both variants under the same180s limit; P remains smaller
by82 cells/17 bits. The simpler P
passes instruction safety, scoped legal-old-encoding refinement and actual
public-loaded symbolic-byte phase1 program proofs. Both simulators agree on
the full finite public sweep. Keep all deliberate invalid-encoding behavior
changes and retained proof timeouts explicit; see [E0030](../../evidence/E0030-timed-gpio-comparison/README.md).

Select P only as an isolated experimental candidate for mapped CMOS5L
area/timing comparison against compact10 with identical conditions. Do not
promote production RTL or claim physical fit from generic cell counts.
Do not add instruction packing or pursue the seven-word mode1 optimization in
this slice. Preserve the input-hold contract, real eight-word loader and old
SPI gates. A future mapped result should determine whether the generic saving
survives real library/timing constraints before expanding the architecture.
