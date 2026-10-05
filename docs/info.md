<!-- Modified 2026-10-05: M1 runtime-readback and bounded-RX candidate datasheet. -->
## How it works

This is an M1 simulation candidate for the Protocol Emulator ASIC. A bounded
SET/WAIT/HALT/WAIT_PIN/LOOP/SHIFT_STEP engine executes up to eight public-pin-loaded words. Active-low
synchronous reset clears PC, state, wait count, GPIO value and GPIO direction;
reset wins over enable. `uio_out/uio_oe` expose the logical GPIO bank and
`uo_out` normally exposes execution state/ready/PC. Dedicated inputs control
the loader or nonintrusive runtime register readback.

The synchronous loader supports byte writes, length commit, and readback.
Each `uio_in` bit has a two-stage clocked synchronizer. `WAIT_PIN` observes the
second stage and either faults or conditionally skips after its explicit
accepted-edge timeout. A three-word programmed kernel demonstrates bounded
event and timeout paths to HALT. This is an RTL latency contract, not analog
metastability evidence.

A non-nested counted-block instruction repeats an immediately following body
0..255 times. A one-bit shift step composes with that loop to send and receive
eight-bit payloads in either bit order. TX payload and RX result/valid registers
are public-pin accessible. A timed byte burst composes with framing firmware
for a qualified digital 8N1 UART-TX waveform. The bounded UART-RX candidate
validates two frames but delivers only the last byte after both pass; raw-valid
does not mean frame accepted. It is not a continuous/lossless receiver, SPI,
I2C, or electrical-compliance result.

## How to test

Hold `rst_n` low through a rising edge, then deassert it before a later edge.
Use `ui_in[7:5]` for loader mode/write/register-space selection, `ui_in[4:0]`
for byte/register address, and `uio_in/out` for data. Register-space address zero
commits program length; addresses 1..4 expose TX, raw RX, raw-valid and TX-alt. Commit length
last, release loader mode, and execution begins at word zero. See
`docs/specs/m1-program-loader.md`.

With `ui_in[7:5]=011`, register data instead appears on dedicated `uo_out`
without resetting execution or taking ownership of `uio`. Select `ui_in=00`
for status, `62` (hex) for raw RX, or `63` for raw-valid. See
`docs/specs/m1-runtime-readback.md` and `docs/specs/p-uart-rx-8n1.md` for the
read timing and bounded batch acceptance policy. Loader reads drive all `uio`
pins and are unsafe while an external push-pull RX source is connected.

## External hardware

No external hardware result is claimed. The 50 MHz flow value remains a target;
this candidate has no new CMOS5L timing, fit, gate-level or silicon evidence.
