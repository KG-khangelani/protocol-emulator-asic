# P-SPI-HOST-MODE0 feasibility seed

Status: proposed, simulation-only partial seed, 2026-11-03. This does not replace
P-SPI-HOST-4MODE: that comparison still requires 1 MHz, modes 0-3, both bit
orders, full duplex and chip-select boundaries. No production RTL/ISA change
is authorized by this document. PR8 and compiler work remain deferred.

## Independent rule and time domain

Mode 0 uses idle-low SCK, rising-edge data observation and falling-edge setup;
see [Microchip's transfer-mode table](https://onlinedocs.microchip.com/oxy/GUID-A9964E93-D46C-42E6-98D2-4ED783ABB2CE-en-US-2/GUID-0E901CC4-8D8D-458D-8FF5-8898F0C41259.html)
and [TI SBOA621, August 2025](https://www.ti.com/lit/pdf/sboa621).
These establish edge conventions, not this chip's electrical timing. SPI
device-specific setup, hold and output delays must be stated separately.

An execution clock is 20 ns at the shared 50 MHz target. Half-period H=25
therefore produces the comparison point of 1 MHz; this is not measured Fmax.
Quarter-clock ticks describe external response phase. A raw transition at an
integer execution edge is applied 1 ps before that edge in simulation. GPIO
updates settle after the edge. This deterministic ordering is not metastability
or analog evidence. The synchronizer consumed at edge n represents raw edge
n-2. Enable is continuously high during a normal transaction.

## Pins, loading, reset and bounds

| Public GPIO | Function | Runtime owner |
|---:|---|---|
| 0 | MOSI | host after first shift |
| 1 | MISO | external target; host always releases |
| 2 | SCK | host from CS assertion |
| 3 | active-low CS | host from assertion through HALT |
| 4..7 | unused | released |

During reset and loading the target is detached. External pulls resolve released
CS high and SCK/MOSI low; they add no chip state. Load/read back the full image,
write TX register 1, leave loader mode, present idle MISO=1 and execute two
disabled synchronizer-flush edges. No protocol input is driven during loader
readback, which would otherwise contend. Runtime result/status reads use
ui_in=0x62/0x63 and dedicated uo_out, never loader mode.

Reset wins over enable and releases all GPIO, erases image/data and aborts the
transaction. Entering loader mode also aborts execution. Disabling during CS
low freezes GPIO/execution while the synchronizer continues: it stretches SCK
and invalidates the fixed-rate transaction. It is not successful completion;
reset/reload is required for acceptance. There is no SPI clock stretching,
external wait or unbounded loop in this seed.

## Eight-word coupled-shift candidate

Both bit orders use the same image shape, eight iterations and public TX data.
Late shifting maximizes MISO response time without changing the existing ISA.
An early-shift ordering is retained as a falsification control.

| PC | Late candidate | Early control difference |
|---:|---|---|
| 0 | LOOP(length=5,count=8) | same |
| 1 | SET SCK=0, CS=0, enable those outputs | same |
| 2 | WAIT(H-3) | SHIFT_STEP(MOSI=0,MISO=1,order) |
| 3 | SHIFT_STEP(MOSI=0,MISO=1,order) | WAIT(H-3) |
| 4 | SET SCK=1 | same |
| 5 | WAIT(H-2) | same |
| 6 | SET SCK=0, CS=1 | same |
| 7 | HALT | same |

For bit index j=0..7, low-phase start L_j=2+2Hj and rising edge R_j=L_j+H.
Late SHIFT_STEP executes R_j-1; early SHIFT_STEP executes L_j+1. CS asserts on
edge 2. Falling edges are 2+2H(j+1), with final falling/CS deassertion together
on edge 2+16H. Thus CS setup and post-final-rising hold are H clocks. HALT is
edge 3+16H at PC7. At H=25: rising edges 27,77,...,377; release 402; HALT 403.
Every SCK high and inter-bit low interval is exactly H clocks.

MOSI may change during the low phase and must be stable at least one execution
clock before each rising edge. It remains stable through the high phase. A
target launches MISO after each L_j with a fixed response d quarter-ticks,
1<=d<=4H-4, and holds it until the next low-phase response. Even the latest
response meets this seed's one-clock input setup; data is constant across each
rising edge. The target holds the last bit through CS deassertion and releases
at the following quarter tick, after the host output settles. Idle MISO is 1.
These are explicit digital test conditions, not a
claim about every commercial target or electrical timing limit.

The external oracle assembles MOSI/MISO at R_j, independently of the VM. The
actual coupled shifter consumes raw input at R_j-3 for the late candidate.
Its latest observable response is therefore d=4(H-3). The interval after that
deadline and before 4H-4 is deliberately tested; it cannot be silently excluded
to call the whole seed PASS. A green regression that reproduces a mismatch is
falsification evidence, not successful SPI receive qualification. This is a
test of these explicit schedules, not an impossibility proof for every program.

Raw-valid asserts on the eighth SHIFT_STEP, before the eighth rising SCK edge.
It cannot alone accept a transaction. Only known-image HALT with exact pin
trace, no abort and RX equal to the independent rising-edge word can accept it.

## Isolated phase-separated reference experiment

Assess generic DRIVE and SAMPLE operations separately from the production VM.
DRIVE prepares a TX bit without consuming RX; SAMPLE consumes synchronized RX
without changing MOSI. Alternation is required; repeated DRIVE, SAMPLE without
DRIVE, configuration changes and partial HALT fault. Reset clears the prepared
flag; disable freezes it. No encoding or RTL implementation is selected.
Only this phase-only plan and its listed guards are assessed. Interleaving
legacy SHIFT_STEP/burst instructions with the new operations is outside the
reference contract; backward-compatible mixed-mode behavior still needs design.

The reference plan is LOOP(length=7,count=8), then a seven-word body: SET low,
DRIVE, WAIT(H-3), SET high, WAIT(0), SAMPLE, WAIT(H-4); followed by SET release
and HALT. SAMPLE at R_j+2 consumes raw R_j. External clock/CS/HALT times match
the eight-word candidate. Count actual words, cycles and declared reference
state. Ten words (320 used bits) do not fit the real eight-word store. A simple
ten-word store would require 64 additional program bits; this alternation guard
adds one reference flag. The real loader has only five byte-address bits (32
bytes), while ten 32-bit words need 40 bytes and six address bits. A pin-preserving
bank/window protocol and its state/logic would also need accounting; storage
alone is not a complete-chip cost. The reference flag is not a minimum-state
proof; recoding existing state remains unexplored. These are candidate costs, not synthesized
CHIP_COMPLETE area, a proven minimum or permission to enlarge production memory.

## Verification obligations

- Check independent rising-edge decoding, exact pulses, CS, direction and bounds
  against every public execution edge; do not inspect internal engine state.
- Enumerate byte values/orders in the model, exercise response phases including
  the one-quarter-tick deadline crossing, and preserve a concrete counterexample.
- Load/read back the real eight-word image on both simulators, check conditional
  successes and expected failures, immediate raw readback, reset/disable/reload.
- Exercise the phase reference's late response, invalid ordering and reset/freeze;
  explicitly reject its use as an eight-word public-loader result.
- Keep source/evidence hashes for the existing visualizer unchanged. No new
  physical, all-four-mode, standard-compliance or owner-fluency result follows.
