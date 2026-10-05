# D16: Add a timed reusable byte burst before UART-specific RTL

Date: 2026-10-05. Status: accepted for the P-UART-TX-8N1 candidate.

## Decision

Extend the existing shifter with a timed eight-step burst and two alternating
public TX payload slots. Keep UART start and stop cells as ordinary SET/WAIT
firmware and use the existing bounded LOOP for two frames. Do not add a fixed
UART state machine.

## Rationale

- A one-bit SHIFT_STEP plus WAIT does not fit a bounded two-frame 8N1 program in
  the existing eight-word public store.
- A timed burst reuses the existing shift registers, bit count and wait counter;
  it is also applicable to SPI-like fixed-period serial words.
- Two payload slots provide a small bounded source for independently chosen
  back-to-back bytes without writes during execution or a protocol-specific
  FIFO. This is a candidate choice, not a proof of minimum storage.
- The existing outer LOOP provides the frame count, so the burst needs no frame
  counter and still terminates at HALT.
- Expanding program storage or adding nested loops would carry substantially
  more state before demonstrating that timed shifting is useful.

## Consequences and falsification

The candidate adds one payload byte, a latched period and a slot selector. A
zero period denotes ordinary execution and a legal nonzero period denotes a
burst or its final hold. Removing the separately retained wait-mode and
burst-mode flags reduces state by two bits without changing instruction timing.
The final generic screen measures 2,783 abstract cells and 410 state bits,
+249 cells and +25 bits over the merged K-SHIFT-8 baseline; see E0016.
If the extension cannot express
the frozen eight-word program, misses any 434-edge boundary, needs UART-specific
control, or costs more than a simpler measured alternative at the complete-chip
boundary, it must be revised or rejected. Passing RTL/formal checks will not be
reported as CMOS5L timing, fit, protocol compliance, or silicon evidence.
