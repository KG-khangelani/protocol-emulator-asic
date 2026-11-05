# D21 - Test serial phase separation before extending the production VM

Date: 2026-11-03. Status: adopted experiment boundary; no ISA selection.

The owner requested continued chip engineering. With PR8's UART host service
and compiler work explicitly deferred, M3-T01's independent SPI mode-0 seed is
the next bounded comparison. Learning remains separate and M0 fluency PENDING.
PR9's visualizer was merged at `ae13f6b`; its source and behavior stay intact.

Freeze [the seed contract](../specs/p-spi-host-mode0.md) before any RTL change.
Test a real public-pin-loaded eight-word SET/WAIT/LOOP/SHIFT_STEP image against
an external mathematical clock/CS/data oracle. Mode 0's opposite setup/sample
phases cannot be assumed from an existing serializer's name.

E0020 falsifies the proposed late schedule over the declared response envelope:
TX `0x96`, target RX `0x69`, H=25 and response 89 quarter-ticks produce raw RX
`0xb4`, even though rising-edge target data has 55 ns of digital setup. Both
Icarus and Verilator reproduce it at unchanged production source. The engine
implements its existing contract: its coupled shift samples synchronized input
before the target's new bit is observable. This is not an RTL defect under the
current M1 specification, or an impossibility proof for every possible image.

Do not hide this result by narrowing test stimulus or presenting green
falsification regressions as SPI qualification. The early-shift control fails
even for the fast target. The optimized late schedule works only for the
stronger response bound of 88 quarter-ticks at H=25. Raw-valid precedes the
final SCK sampling edge, so neither raw-valid nor HALT alone accepts a byte.

An isolated, unencoded DRIVE/SAMPLE reference reuses the existing shifter,
WAIT and LOOP semantics and separates TX preparation from RX observation. Its
SAMPLE at rising-edge+2 consumes the desired synchronized raw rising-edge bit.
Measured reference execution retains 403 accepted edges, but its image grows
from eight words/256 used bits to ten/320. This simple model adds a prepared
flag; state recoding has not been evaluated and no minimum-state claim follows.
The public loader rejects length ten. A larger store also exceeds the real
five-bit byte-address window: 40 bytes require six address bits. Extra program
bits alone omit the required loader banking/window logic and state.

Keep production RTL, pins, configuration, storage and visualizer unchanged.
Do not choose a capacity expansion or protocol-specific engine before comparing
complete-chip costs. The next experiment must freeze encodings/atomicity for a
compact phased operation versus the two-operation/banked-store alternative,
then measure isolated generic implementations under the same oracle. Gate
cost, area/timing and all-four-mode qualification remain NOT_EVALUATED.

E0019/D19 stay reserved for deferred PR8; E0020/D21 do not import that branch.
