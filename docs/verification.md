# Verification plan

Keep functional simulation, generic synthesis, technology-mapped synthesis,
physical timing and real hardware observations as separate evidence categories.

| Layer | Current implementation | Next evidence |
|---|---|---|
| Repository consistency | `tools/check_project.py` | Metadata, pinout and clock agreement |
| RTL | `test/test.py`, seed 20260922 | Wrap, reset priority, hold/resume, input noise, defined pin direction |
| Generic synthesis | `make synth` | Structural sanity; no latches/check errors |
| CMOS5L hardening | Official `gds` workflow | Mapping, placement, routing, precheck, timing and area |
| Gate-level | Official `gl_test` action and same pin-level tests | Agreement after mapping |
| Formal | Not implemented | M1 reset, PC bounds, exact waits and bounded progress |
| Protocol differential | Not implemented | Independent UART/SPI/I2C waveform oracles |
| FPGA | Upstream optional workflow; not tested | Board, bitstream, constraints and analyzer traces |

For each future protocol scenario vary payload, phase, clock ratio, reset,
stalls and adversarial input transitions. Preserve seed, failing waveform and
smallest reproducer. Explicitly state whether external waits have a timeout.

An experiment record needs its question, source revision/hash, configuration,
command, tool versions, observations, limitations and next decision. Preserve
negative evidence. Large reports/GDS belong in immutable release or CI artifacts
with identifiers and SHA-256; keep concise results and links in this repository.
