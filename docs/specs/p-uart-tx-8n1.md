# P-UART-TX-8N1 acceptance contract

Status: implemented local RTL/formal candidate, 2026-10-05; independent review
passed, exact-head CI pending. Evidence: E0016.

## Question and evidence boundary

Can the current reloadable executor transmit two distinct back-to-back UART
8N1 frames at a declared 50 MHz timing point without a UART-specific RTL state
machine? Passing this contract is `PASS`/`MEASURED` only at the RTL/formal rung
for the digital waveform below. It is not baud tolerance, pad slew, analog,
gate-netlist, CMOS5L timing/fit, or silicon evidence.

The workload period is exactly 434 accepted edges, approximately 115.2 kbaud
at the 50 MHz experimental clock target. `ena` remains one during a frame.
Reset or disable has the existing architectural meaning, but a disabled edge
stretches wall-clock UART timing and therefore is not a valid workload trace.

## General timed shift-burst extension

Opcode `10`, bit 29 one retains the K-SHIFT-8 order and pin fields. Bit 21
selects the execution form:

| Field | Manual SHIFT_STEP | Timed SHIFT_BURST |
|---|---|---|
| `[31:30]` | `10` | `10` |
| `[29]` | `1` | `1` |
| `[28]` | bit order | bit order |
| `[27:25]` | TX pin | TX pin |
| `[24:22]` | RX pin | RX pin |
| `[21]` | `0` | `1` |
| `[20:5]` | zero | accepted-edge bit period, 2..65535 |
| `[4:0]` | zero | zero |

Equal TX/RX pins, a period below two, or any reserved-bit violation faults at
the current PC without changing GPIO or committing RX data. Manual SHIFT_STEP
semantics remain unchanged and always use payload slot zero. Starting a burst
while a manual byte is incomplete also faults without a GPIO or RX commit.

On a valid SHIFT_BURST execution edge, the engine loads the selected payload,
drives/samples bit zero in the chosen order, retains the instruction PC, and
enters an internal timed-shift wait. Later bits are driven and sampled exactly
`period` accepted edges apart without fetching another instruction. The eighth
bit commits RX result/valid on that same edge, clears active shift state, and
toggles the selected payload slot. The final data bit is held for one complete
period; the engine then advances PC using the existing LOOP rule and the next
instruction executes on that period boundary.

The existing wait counter supplies the interval. Additional retained engine
state is limited to the latched period and the payload-slot selector. A zero
period denotes ordinary execution; a nonzero period identifies timed-shift wait
including its final hold, so no separate mode latch is required. Reset or
loader-mode reset aborts a burst, clears its timing state and
selects slot zero. `ena=0` freezes PC, counter, GPIO and all shift state. HALT is
not fetched during a burst. Other GPIO value/direction bits are preserved; TX
is driven and RX is released on every bit edge.

## Public data registers

Data/control address 1 remains TX payload slot zero. Address 4 becomes TX
payload slot one. Both are eight-bit read/write registers, reset to zero; a
write to either invalidates an older RX result. Addresses 2 and 3 retain RX
result and RX-valid. Addresses 5..31 remain reserved, read zero and ignore
writes. Entering loader mode resets the engine slot selector but preserves both
payload registers until sampled chip reset.

## Eight-word public program

For period `P`, the independent program generator uses ordinary WAIT count
`P-2` and this exact image:

| PC | Instruction | Purpose |
|---:|---|---|
| 0 | `SET(mask=1, oe=1, value=1)` | establish driven idle high |
| 1 | `LOOP(length=5, count=2)` | emit two complete frames |
| 2 | `SET(mask=1, oe=1, value=0)` | start bit |
| 3 | `WAIT(P-2)` | make start-to-data interval exactly P |
| 4 | `SHIFT_BURST(LSB, tx=0, rx=1, period=P)` | eight data bits |
| 5 | `SET(mask=1, oe=1, value=1)` | stop bit |
| 6 | `WAIT(P-2)` | hold stop through next start or HALT boundary |
| 7 | `HALT` | bounded normal termination |

The first payload comes from slot zero and the second from slot one. At P=434,
SET idle is accepted edge 1, LOOP edge 2, first start edge 3, first data bit edge
437, first stop edge 3909, second start edge 4343, second stop edge 8249, and
HALT edge 8683. Each start, data and stop cell lasts exactly 434 accepted-edge
intervals. The two frames are back-to-back: the second start replaces the first
stop exactly one period after the stop edge, with no extra idle cell.

## Independent oracle and falsification

The oracle is a pure frame function, not the engine model: idle is one, start is
zero, data is payload bits 0 through 7, and stop is one. It maps accepted edge
index to the required pin level and direction for two distinct payloads.

Acceptance requires:

1. both Icarus and Verilator match the public-pin oracle for every byte value;
   pair byte `x` with `255-x` so every value appears in both payload slots;
2. the exhaustive RTL sweep uses a reduced legal period to isolate framing and
   data ordering, while retained cases `00/ff`, `55/aa`, `aa/55`, and `ff/00`
   run at the exact 434-edge period;
3. the independent semantic model enumerates all 256 pairs at period 434;
4. formal properties prove arbitrary legal-period countdown, bit-edge spacing,
   slot selection/toggle, eighth-edge result capture, final hold, reset and
   enable freeze; covers reach both payload slots and normal completion;
5. public loader readback checks both payload slots and the eight program words;
6. malformed burst fields, period 0/1, reset mid-frame, and disable injection
   fail closed or freeze exactly as specified;
7. the accepted-edge transition list is retained on failure and no physical or
   standards-compliance status is inferred from simulation.

Any wrong bit, early/late boundary, extra idle cell between frames, failure to
HALT at the bound, simulator/model disagreement, or payload-slot ordering error
is FAIL.
