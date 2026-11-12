# D42 - Screen synchronous SRAM with preserved instruction timing

Date: 2026-11-12. Status: engine/store and full protocol gates pass; complete
mapped footprint falls 78.5306%. Advance to physical integration; production
is unchanged and the physical gate remains open.

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

Both simulators now pass the complete 30-group protocol matrix with only the
declared clocked program-read helper. All 1,052 SPI, 1,160 I2C, four boundary,
36 abort records and the 44-byte bank control match their unchanged references.
The [predeclared mapped screen](../specs/g2-sram-mapped-screen.md) reproduces
D39's 477,788.2578 square-micrometre reference exactly. The SRAM candidate has
4,200 standard cells / 53,089.7598 square micrometres and one real macro /
49,488.4992 square micrometres: 102,578.259 total, 78.5306% lower. State outside
the macro falls from 4,278 to 353 flip-flops. Actual netlist connectivity and
selected library areas are audited; this clears the declared 20% screen.
All 106 SRAM-side lint warnings concern the black-box header's timescale;
there are no latch, width, mapping or synthesis errors. Remove the irrelevant
header timescale for the separate physical integration trial.

The SRAM fast-library temperature
differs from the existing standard-cell corner; freeze an honest, explicit
physical model before any full qualification run.

E0042 records the installed macro's feasibility inputs and the actual isolated
candidate, proofs, observed faults, complete regression, matched mapping and
retained failed attempts. All three retained replays pass. No routed/timing,
precheck or real-netlist pass is claimed yet. G1, D39, failed trials, production and owner-fluency
status remain separate.

The clean 95120d8 CI run now passes all three gates. Its three original ZIPs
and 1,359 files pass the semantic/source/runtime replay, including the actual
proof models, observed faulty-store behavior, both exact 30-group suites and
unchanged records. Each job binds its loaded workbench to the tested source.
See [the CI evidence](../../evidence/E0042-sram-prefetch-screen/ci-95120d8/README.md).
