# D42 - Screen synchronous SRAM with preserved instruction timing

Date: 2026-11-12. Status: engine/store screen passes; full regression running;
physical gate open and production unchanged.

E0040 rejects the banked-read implementation's mapped cost. E0041 shows that
clock spacing alone leaves substantial congestion. Stop those branches and
test the pinned PDK's SRAM as a general program-store implementation.

The [screen contract](../specs/g2-sram-prefetch-screen.md) preserves the 128-word
logical capacity, every instruction and the frozen UART/SPI/I2C timing
boundaries. It declares clocked program-byte readback and interface identifier
0x22, rather than pretending the old combinational loader is unchanged.
A real word-valid vector provides zero-after-reset semantics; a word-zero
shadow and look-ahead fetch are intended to preserve instruction cadence.
The actual implementation now passes its engine/store proof and fault checks.

Two whole-chip refactor proofs retain their 120-second timeouts. The explicitly
declared compositional follow-up proves all 128 actual engine state bits and
all 128 original engine output bits, with an independent reset base and
byte-identical surrounding modules. This proves the engine refactor; SRAM
integration has separate obligations. The full vendor 8,192-bit memory model
passes arbitrary-logical-word induction, four coverage witnesses and a checked
partial-write-mask counterexample. Both simulators pass the store-port suite
and expose each of four deliberately faulty implementations. All 22 historical
default groups still pass in both simulators. E0042's retained replay passes.

Run the complete 30-group protocol matrix in both simulators with only the
declared clocked program-read helper; its current run is unfinished. Measure
whole-chip cost only after those gates. The SRAM fast-library temperature
differs from the existing standard-cell corner; freeze an honest, explicit
physical model before any full qualification run.

E0042 records the installed macro's feasibility inputs and the actual isolated
candidate, proofs, observed faults and retained failed attempts. Its footprint
is not a chip-area result; no complete-protocol or physical pass is claimed
yet. G1, D39, failed trials, production and owner-fluency
status remain separate.
