# P-SPI-HOST-4MODE timing and schedule screen

Status: frozen reference-screen contract, 2026-11-11, baseline f9dcd8a.
No RTL, public loader, memory capacity or physical-interface change is made.
This screen checks instruction schedules; actual four-mode RTL execution is
NOT_EVALUATED until a separate public-pin experiment.

## Edge conventions and fixed comparison conditions

[Microchip's transfer-mode table](https://onlinedocs.microchip.com/oxy/GUID-DDF2C9BC-07FB-4ABF-938A-774B157B4519-en-US-11/GUID-0E901CC4-8D8D-458D-8FF5-8898F0C41259.html)
and [clock-control register description](https://onlinedocs.microchip.com/oxy/GUID-80B1922D-872B-40C8-A8A5-0CBE009FD908-en-US-3/GUID-C6974F86-9EF8-4215-A97F-0A3924201AB3.html)
supply the polarity/phase conventions. Timing margins below are this project's
digital comparison conditions, not universal device electrical limits.

| Mode | CPOL | CPHA | First edge | Second edge | Sample |
|---|---|---|---|---|---|
| 0 | 0 | 0 | rising | falling | first |
| 1 | 0 | 1 | rising | falling | second |
| 2 | 1 | 0 | falling | rising | first |
| 3 | 1 | 1 | falling | rising | second |

Use the existing pin mapping: MOSI0, MISO1, SCK2, active-low CS3; others released.
The core period is20ns and H=25 clocks per half-period, giving a1MHz target,
not measured Fmax. Both bit orders transfer exactly eight bits. Reset/loading
release outputs; fixed external pulls resolve CS high and SCK/MOSI low.
The target is detached during public loading/readback. Two disabled input
flush edges precede execution. Execution then has continuously high enable.

SCK must already resolve to CPOL for at least one complete core interval before
CS asserts. It cannot change on the CS-assertion edge. Establishing CPOL=1
while CS is high therefore needs explicit scheduling on the fixed-pull board.
CS setup and hold are each at least H core intervals. These margins retain
the mode-0 comparison point and cannot be shortened to rescue a word count.

For CS assertion A and j=0..7:
- First edge L_j=A+H+2Hj.
- Second edge T_j=A+2H+2Hj.
- Sample S_j=L_j for CPHA0, T_j for CPHA1.
- MOSI/target launch D_j=A+2Hj for CPHA0, L_j for CPHA1.
- CS release Q=max(T_7,S_7+H); HALT is Q+1.

SCK alternates at all16 edges and has exact H intervals between edges.
MOSI changes only at D_j and stays stable across the sample edge; MISO always
remains an input. HALT or valid alone is insufficient: accept only after the
known image halts with all pin, boundary, direction and data checks satisfied.
Reset/reload aborts; disabled execution invalidates fixed-rate acceptance.

## Two input contracts, kept separate

HELD_RESPONSE: each target bit arrives between5ns and480ns after D_j, with
per-bit response allowed to vary, and remains until the following launch's
response. The last bit remains through CS release. This gives at least20ns
setup at S_j. This is the original held-data envelope, generalized to phase.

EDGE_ONLY: the intended bit is guaranteed only at sampled core tick S_j;
other ticks may vary independently. This is the discrete formal premise used
by E0025, not an electrical aperture specification. A deterministic stress
witness supplies the complement at other ticks. No held-data guarantee can
be inferred from this weaker premise.

The actual input synchronizer's consumed value at execution n is raw n-2.
Exact capture at S_j+2 can support either profile. A later capture must account
for an additional input hold obligation explicitly.

## Predeclared schedule families

All images use existing compact DRIVE(aux GPIO), SAMPLE(delay), SET, WAIT,
LOOP and HALT semantics. No new opcode or engine is assumed.

EXACT: five-word loop body DRIVE, WAIT(H-2), SET opposite SCK,
SAMPLE(delay1), WAIT(H-4). Capture S_j+2. Prepend idle establishment;
CPHA1 also prepends CS assertion and WAIT(H-3) before LOOP. This places A=3
for CPHA0 and A=2 for CPHA1 and satisfies the common external schedule.

HELD: same external schedule, but combine SAMPLE and the final WAIT into
SAMPLE(delay H-2). Capture S_j+H-1, consuming raw S_j+H-3. At H25 this requires
the bit through S_j+22 (440ns after the wire sample). That follows from
HELD_RESPONSE and does not follow from EDGE_ONLY. Count the removed word.

NAIVE: change clock values in the old eight-word mode-0 image, without adding
idle/CS preamble. Check it against the same boundary contract with A=2.
Preserve any rejection, even if its payload or steady clock looks plausible.

The reference-only executor permits up to16 words to measure schedules beyond
the real eight-word capacity. This permission exists only in the model.
Every result must report used words/bits, fits-eight status and RTL execution
NOT_EVALUATED. Neither9 nor10 nor11 reference words may masquerade as a
public-loaded eight-word result. These three families are not an exhaustive
program search and cannot establish an ISA minimum or impossibility.

## Validation and stopping rule

Cross-check literal edge tables independently of encoded instructions. Screen
the byte alphabet in all modes/orders for EXACT under both profiles and HELD
under HELD_RESPONSE; exercise response extremes and deterministic per-bit
jitter. Retain HELD/EDGE_ONLY and NAIVE boundary counterexamples. Reject wrong
clock phase, early CS release and MISO contention in oracle mutation controls.
Keep source hashes and representative public-style traces. Run all work in
the locked container and add the reference checks to CI.

Do not change RTL in this slice. The next action follows the measured result:
public-load any fitting candidate on both simulators, or investigate a declared
capacity/timing tradeoff if the required schedule does not fit.

## Scoped public RTL screen

In this slice also load only fitting eight-word HELD mode0/2 images through
the actual compact public interface, on both simulators: six byte patterns
per mode/order (24 positive), four edge-only negative controls and all eight
NAIVE mode/order controls (two expected positive, six negative). Each trace
uses raw input values at sampled core ticks, applied1ps before the rising
edge; this is not a sub-cycle noise or electrical qualification. Check actual
public pins, readback, status and raw/valid on every edge against the same
independent oracle. Require36 cases per simulator and identical records.
Do not load oversized references or change candidate/production RTL.
