# Programs for interface 0x22

These thirteen readable sources target the unchanged G2-qualified SRAM core.
The catalog pins their original hand-encoded words and binary hashes. Changing
an example's bytes requires an explicit version/migration decision; rebuilding
never silently updates the catalog. See [the programming guide](../../docs/programming.md).

| Source | Pins and payloads | Contract |
|---|---|---|
| `uart_tx.asm` | TX pin 0, dummy RX pin 1; TX0=55, TX1=AA hex | Two 8N1 frames, LSB first, 434 accepted edges per bit; HALT edge 8683 |
| `uart_rx.asm` | RX pin 1; dummy TX pin 0, both TX payloads FF hex | Two bounded 8N1 frames; last-byte storage, framing validation and explicit host service |
| `spi_mode0_lsb.asm` / `spi_mode0_msb.asm` | MOSI 0, MISO 1, SCK 2, CS 3 | CPOL=0, CPHA=0; held-input contract |
| `spi_mode1_lsb.asm` / `spi_mode1_msb.asm` | Same SPI pins; TX0=96 hex | CPOL=0, CPHA=1; held-input contract |
| `spi_mode2_lsb.asm` / `spi_mode2_msb.asm` | Same SPI pins; TX0=96 hex | CPOL=1, CPHA=0; held-input contract |
| `spi_mode3_lsb.asm` / `spi_mode3_msb.asm` | Same SPI pins; TX0=96 hex | CPOL=1, CPHA=1; held-input contract |
| `i2c_write.asm` | SCL 0, SDA 1, outcome marker 2..4 | Write 96 hex to 7-bit address 52 hex |
| `i2c_read.asm` | Same I2C pins | Read one byte from address 52 hex, finish with controller NACK |
| `i2c_write_read.asm` | Same I2C pins | Write, repeated START, read and controller NACK |

Payloads are ordinary public data registers, so rebuilding is unnecessary when
only a transmitted byte changes. The external test target supplies RX=69 hex;
that receive value is an oracle expectation, never a compiler input. I2C TX0
holds the address byte and TX1 the data byte; repeated START overrides the final
address R/W bit through the already-qualified general instructions.

All timing uses a continuously enabled 50 MHz target clock. UART P=434 gives
50,000,000/434 baud (approximately 115,207). RX uses a two-frame batch with one
raw-result register: a host must cache the first byte, validate final HALT and
then copy the second. The D19 reference host requires polling gap H >= 1,
copy latency L >= 1 and **H + L <= 10P** accepted clock edges. No completed pair
is delivered after a framing fault or interrupted run. Terminal-only readback
can recover only the last byte; it does not demonstrate lossless continuous RX.

SPI half-period is 25 accepted edges. The declared MISO hold profile permits
the delayed sample and two-stage synchronizer; compatibility with a peripheral
that supplies data only on the nominal sample edge is deliberately rejected.
The test target checks both early and late legal responses and the edge-only
negative for every mode/order.

I2C has the frozen digital Standard-mode 100 kHz limit, open-drain output and
external pull-ups. Clock stretching, NACK and timeout cleanup remain bounded by
the original contract. Outcome marker values are 1=OK, 2=NACK, 3=TIMEOUT.
The target model verifies resolved bus ownership, final-edge priority and the
one-tick-late rejection. Analog rise time, electrical board behavior and
fabricated-silicon interoperability are outside this digital demonstration.

The toolchain test changes the UART period, SPI sample delay, I2C open-drain
operation and I2C timeout to verify that independent oracles reject wrong
programs. It also checks bad UART framing and interface/readback mismatches.
The examples themselves retain their original qualified bytes.
