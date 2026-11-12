# Phase-1 capacity screen with unchanged instructions

Frozen experiment: 2026-11-12. Baseline 969323d.
Keep the actual eight-word store, public loader, candidate/production RTL,
pin mapping, H25 clock period, CS setup/hold and held-response envelope unchanged.

## First-edge boundary

The pin contract requires one complete idle-clock interval before CS asserts.
With the fixed SCK pull-down, mode1 may use interval [0,1] and assert CS at
execution edge1. The oracle's previous A>=2 parameter check unnecessarily
excluded that case. Permit A>=1 while retaining the observed idle-before-CS
and complete waveform checks. Mode3 still fails at A1 on this board because
its initial resolved SCK is low. Add independent boundary/mutation tests;
do not shorten the 25-tick CS setup/hold to save a word.

## Declared finite search family

One LOOP(count8), a four-instruction body containing one each of DRIVE,
WAIT, SET-clock and SAMPLE, then SET-release and HALT. The first body
iteration starts with no prepared bit. Leading DRIVE, trailing SET and
capture belong to the same iteration. No shifted iteration attribution,
warm-up data operations, head/tail unrolling or alternate payload protocol.

Enumerate all24 body orders and WAIT/SAMPLE counts0..49. Timing filtering
requires50 ticks per iteration, SET25 ticks after DRIVE, and capture2..24
ticks after SET. Represent four GPIO-mask combinations: DRIVE and SET each
may update clock alone or clock plus asserted CS. Count timing rejection
reasons before reference execution.

Enumerate prefixes of length0..3 over IDLE, ASSERT-CS and WAIT(0..49), with
at most one WAIT. Repeated SETs are allowed. This is865 prefixes per body.
Screen modes1/3 with TX96/RX69, MSB-first; derive CS from the program's first
actual low resolved CS and apply the independent full timing oracle.
Report counts by mode and total words, rejected classes, accepted programs
and minimum only within this declared family. A single counterexample
rejects universal acceptance of a candidate. Never claim an ISA lower bound.

## Positive witnesses and controls

For the best declared references, test both orders across the RX byte
alphabet with a one-to-one TX permutation, using earliest, latest and mixed
legal response delays (3,072 positive model transactions total). Retain four
mixed-byte edge-only failures. These are paired byte samples, not every TX/RX
pair and not RTL successes.

Also enumerate every deletion producing eight words from the nine-word
mode1 reference and ten-word mode3 reference:9+45 images, both orders.
Run all108 on the actual compact public loader/readback and pin oracle in
both Icarus and Verilator. Require the expected rejection; retain traces
even if a received byte is correct. Check length9/10 commit rejection on the
real loader without writing beyond its32 legal byte addresses (four cases
including both orders). The reference model's16-word allowance never widens
the real hardware. No enlarged-store success is claimed.

Budgets: one180s bounded family search, one180s reference sweep, and180s per
simulator, with no enlarged adaptive budget. Preserve errors/timeouts.
Keep E0028's held mode0/2 proof and prior SPI gates in CI. Use the result to
choose a subsequent bounded search or measured general-purpose hardware
tradeoff; do not add an instruction or enlarge storage in this slice.
