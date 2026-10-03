# Verification plan

Keep functional simulation, generic synthesis, technology-mapped synthesis,
physical timing and real hardware observations as separate evidence categories.

| Layer | Current implementation | Next evidence |
|---|---|---|
| Repository consistency | `tools/check_project.py` | Metadata, pinout and clock agreement |
| Learning-status integrity | `tools/learning_status.py --verify` plus an invalid-promotion self-test | Milestone references agree and an unearned human fluency PASS is rejected |
| RTL | M1 `test/test.py` through Icarus and Verilator, seed 20261002 | Public-pin reload/readback, Python-model agreement, reset/enable, WAIT, K-INPUT-WAIT, K-BOUNDED-LOOP counts 0/1/2/255 and safe invalid behavior |
| Readable waveform | `LearnWaveform` VCD parser plus intentionally corrupted edge | Every M0 rising edge matches the transition table; learner can explain a selected edge |
| Generic synthesis | `make synth` | Structural sanity; no latches/check errors |
| CMOS5L hardening | Official `gds` workflow | Mapping, placement, routing, precheck, timing and area |
| Gate-level | Official `gl_test` action and same pin-level tests | Agreement after mapping |
| GL-shaped harness | RTL compiled with `GL_TEST`, direct-engine handles absent | Public reset smoke catches harness/API drift without claiming gate-netlist evidence |
| Formal | M1 engine, store and input-synchronizer SBY/Z3 proofs/covers plus expected-failing wrong-decrement property; archived M0 evidence retained separately | Preserve event-on-final-edge priority and timeout/freeze properties as the instruction set evolves |
| GDS reproducibility | `tools/compare_gds_records.py` | Separate BGNLIB/BGNSTR timestamp drift from geometry-record differences |
| Protocol differential | Not implemented | Independent UART/SPI/I2C waveform oracles |
| FPGA | Upstream optional workflow; not tested | Board, bitstream, constraints and analyzer traces |

For each future protocol scenario vary payload, phase, clock ratio, reset,
stalls and adversarial input transitions. Preserve seed, failing waveform and
smallest reproducer. Explicitly state whether external waits have a timeout.

An experiment record needs its question, source revision/hash, configuration,
command, tool versions, observations, limitations and next decision. Preserve
negative evidence. Large reports/GDS belong in immutable release or CI artifacts
with identifiers and SHA-256; keep concise results and links in this repository.
