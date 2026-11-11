# D27 - Qualify sensitivity, then extend the protocol contract

Date: 2026-11-11. Local sensitivity qualified; terminal covers inconclusive.

E0025's written conjunction needs explicit negative controls. A wrong public
MOSI goal must produce a reachable counterexample; removing the first input
premise must expose the wrong actual synchronized bit. E0026 satisfies both
while the unchanged baseline still proves.

Actual early-SAMPLE firmware must be loaded/read back against its supplied
bytes. Comparing it with baseline image constants would merely find an image
mismatch. Both simulators instead show correct wire timing/RX0x69 and HALT,
but raw RX0xd3/0xb4; the public acceptance rule rejects it. Preserve these
meaningful controls in a dedicated CI gate.

One concrete full-chip cover times out at180s; the other is interrupted without
a result. Neither justifies a larger budget. Keep finite actual completion
witnesses distinct from formal covers. The written universal proof together
with finite positive/negative traces justifies drafting the next protocol
contract, not production or physical promotion.

Next specify the four CPOL/CPHA mode schedules and input envelopes against an
independent pin oracle before changing RTL. Preserve the faster-target option
without RTL changes and the measured compact/whole-chip cost comparison.
Revisit deep reachability only with a new method and frozen budget. Compiler,
physical and owner-learning claims stay unchanged. E0026 needs no production
or candidate RTL change.
