# D53 — Rehearse the physical UART test on the FabricFox FPGA target

24 November 2026. The Windows host exposed one motherboard COM port and six
Bluetooth serial ports. Present USB devices and mounted volumes did not
identify a project board, independently isolatable UART peer or capture
instrument. The repository specifies a proposed bench and has no configured
connection to one. BENCH-T01 therefore has no physical observation today.

Choose the board-independent prerequisite named in the council bench plan:
implement the receiver on the Tiny Tapeout FabricFox v2 iCE40UP5K-SG48
breakout and test its package-pin behavior. Use the official wrapper and pin
assignments from the support-tools commit pinned by this repository. Keep the
production Verilog and twenty qualified inputs intact. Supply the SRAM
implementation only to the FPGA experiment.

## Decision criteria fixed before building

- Try upstream's deterministic placement seed 10 at the **50 MHz** project target.
  If static timing fails, preserve the failure and try **12.5 MHz** with the
  same released 32-byte receiver. Its 434 clocks per bit then give about
  28,802 baud. Score each frequency independently, with strict timing and
  every used package pin constrained.
- Verify synchronous read, byte-masked write-through, overlapping read/write
  addresses, disabled holds and the chip's 128-word store boundary. Compare
  against the qualified SRAM model and retain a wrong-lane or bypass control.
- Pack and unpack the FPGA configuration. Use the decoded configuration at
  the chosen passing frequency to replay the E0050 cold-load operations on
  external pins, verify all 32 bytes and deliver the two frames `96 69` at
  terminal `A7`. Require rejection of a changed programmed byte, a modeled
  peer driving against readback, and a bad UART stop bit. Repeat the build
  from the committed inputs and compare configuration bytes and observations.
- Budget 90 minutes of wall time from 20:56:11 UTC for this first build and rehearsal. Record
  an unclosed target or unsupported tool as such. A successful offline result
  supplies a bench candidate for the named board. Electrical line release,
  oscillator accuracy and real host-service timing still require a capture.

[Board workflow](../../.github/workflows/fpga.yaml) · [Bench prerequisite](../../evidence/E0049-review-council/panel-b/fixture/bench.md) · [Reference transport](../../evidence/E0050-powered-cold-loader/README.md)
