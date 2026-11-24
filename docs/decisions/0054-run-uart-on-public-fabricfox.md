# D54 — Test the released receiver using a container and a public FabricFox

The fpgas.online Welland site provides a user bitstream loader and a serial
terminal for the on-board RP2350. On 24 November its status endpoint reported
present FPGA boards. The demo harness and E0051 assign the same signals to
the same package pins. This gives us access to a real driver and receiver on
separate chips. The bench's calibrated current and voltage probes remain a
separate requirement for the electrical release claim. [Board service](https://docs.fpgas.online/en/latest/user/boards/tt-fpga/about.html) · [Bitstream interface](https://docs.fpgas.online/en/latest/user/boards/tt-fpga/own-bitstream.html) · [E0051 image](../../evidence/E0051-fabricfox-uart/README.md)

## Test before making a claim

- Use an idle public FPGA board, the existing 104,090-byte E0051 image and
  a RAM-only user test through the documented MicroPython console. Keep
  physical production inputs, public releases and other visitors' designs intact.
- With the RP2350 data drivers released, establish identity `22`. Read all
  32 bytes, length and both payload registers over physical pins. Use the
  E0050 clock and selector sequence. Connect the RP2350's UART driver only
  after byte readback with the clock parked and the chip in loader-write mode.
- Send back-to-back `96 69` at 434 receiver clocks per bit. Use a continuous
  1 MHz receiver clock first, then the 12.5 MHz FPGA target if the slower
  check passes. Accept both bytes only after `A7`. Require a bad stop to
  produce `E6`, discard tentative bytes, and check a deliberately damaged
  program byte at readback. Never drive opposed outputs to create a fault.
- Record the measured service intervals on the RP2350, source clock and baud
  assumptions, board identity, commands, raw receipts and failures. Check
  a fresh cold start. Distinguish physical digital observations, configured
  clock rates and calibrated analog measurements. The container can also
  exercise an independent UART peer against the archived bitstream if
  the remote bench is partly or wholly unavailable.
- Allow 90 minutes from 21:35:14 UTC for this experiment. Retain a partial
  hardware result if the service or fixture cannot supply a measurement.
