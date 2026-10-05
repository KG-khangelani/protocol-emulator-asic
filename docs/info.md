<!-- Modified 2026-10-02: M1 simulation-candidate datasheet. -->
## How it works

This is an M1 simulation candidate for the Protocol Emulator ASIC. A bounded
SET/WAIT/HALT/WAIT_PIN/LOOP/SHIFT_STEP engine executes up to eight public-pin-loaded words. Active-low
synchronous reset clears PC, state, wait count, GPIO value and GPIO direction;
reset wins over enable. `uio_out/uio_oe` expose the logical GPIO bank and
`uo_out` exposes execution state and PC. Dedicated inputs are unused.

The synchronous loader supports byte writes, length commit, and readback.
Each `uio_in` bit has a two-stage clocked synchronizer. `WAIT_PIN` observes the
second stage and either faults or conditionally skips after its explicit
accepted-edge timeout. A three-word programmed kernel demonstrates bounded
event and timeout paths to HALT. This is an RTL latency contract, not analog
metastability evidence. Protocol firmware remains future work.

A non-nested counted-block instruction repeats an immediately following body
0..255 times. A one-bit shift step composes with that loop to send and receive
eight-bit payloads in either bit order. TX payload and RX result/valid registers
are public-pin accessible in loader mode. This is a reusable serial datapath
primitive, not a UART, SPI, I2C, or protocol-rate result.

## How to test

Hold `rst_n` low through a rising edge, then deassert it before a later edge.
Use `ui_in[7:5]` for loader mode/write/register-space selection, `ui_in[4:0]`
for byte/register address, and `uio_in/out` for data. Register-space address zero
commits program length; addresses 1..3 expose TX, RX, and RX-valid. Commit length
last, release loader mode, and execution begins at word zero. See
`docs/specs/m1-program-loader.md`.

## External hardware

No external hardware result is claimed. The 50 MHz flow value remains a target;
this candidate has no new CMOS5L timing, fit, gate-level or silicon evidence.
