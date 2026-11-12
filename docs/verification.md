# Verification plan

Keep functional simulation, generic synthesis, technology-mapped synthesis,
physical timing and real hardware observations as separate evidence categories.

D33's manual GDS workflow stages an E0030-identical P or compact10 chip in CI.
The staged source manifest, not the workflow revision alone, identifies the
synthesized design. Its twelve required public test groups and full SPI sweep
must pass on the actual mapped netlist; the preceding RTL-only harness check
does not qualify physical behavior. See [E0031](../evidence/E0031-8x4-physical-comparison/README.md).

| Layer | Current implementation | Next evidence |
|---|---|---|
| Repository consistency | `tools/check_project.py` | Metadata, pinout and clock agreement |
| Learning-status integrity | `tools/learning_status.py --verify` plus an invalid-promotion self-test | Milestone references agree and an unearned human fluency PASS is rejected |
| RTL | M1 `test/test.py` through Icarus and Verilator, seed 20261002 | Public-pin reload/readback, Python-model agreement, reset/enable, WAIT, K-INPUT-WAIT, K-BOUNDED-LOOP counts 0/1/2/255, K-SHIFT-8 in both bit orders, data-register behavior and safe invalid behavior |
| Readable waveform | `LearnWaveform` VCD parser plus intentionally corrupted edge | Every M0 rising edge matches the transition table; learner can explain a selected edge |
| Generic synthesis | `make synth` | Structural sanity; no latches/check errors |
| CMOS5L hardening | Official `gds` workflow | Mapping, placement, routing, precheck, timing and area |
| Gate-level | Official `gl_test` action and same pin-level tests | Agreement after mapping |
| GL-shaped harness | RTL compiled with `GL_TEST`, direct-engine handles absent, separate FST/JUnit provenance | Public reset smoke catches harness/API drift without overwriting or being labelled as the full RTL waveform; no gate-netlist claim |
| Formal | M1 engine, program store, data store and input-synchronizer SBY/Z3 proofs/covers plus expected-failing wrong-decrement property; archived M0 evidence retained separately | Preserve event-on-final-edge priority, shift completion/capture, result-valid, timeout and freeze properties as the instruction set evolves |
| GDS reproducibility | `tools/compare_gds_records.py` | Separate BGNLIB/BGNSTR timestamp drift from geometry-record differences |
| Protocol differential | Independent UART and partial SPI mode-0 oracles; isolated phase/capacity comparison in `experiments/spi_phase/` | All-four-mode SPI and I2C remain open; candidate results do not qualify production RTL |
| FPGA | Upstream optional workflow; not tested | Board, bitstream, constraints and analyzer traces |

For each future protocol scenario vary payload, phase, clock ratio, reset,
stalls and adversarial input transitions. Preserve seed, failing waveform and
smallest reproducer. Explicitly state whether external waits have a timeout.

An experiment record needs its question, source revision/hash, configuration,
command, tool versions, observations, limitations and next decision. Preserve
negative evidence. Large reports/GDS belong in immutable release or CI artifacts
with identifiers and SHA-256; keep concise results and links in this repository.

The SPI comparison's separate CI step retains candidate sources, hashes, patches,
logs, JUnit and complete-chip generic netlists. Its banked loader intentionally
fails the existing length-nine rejection test; the comparison runner requires
exactly that failure and labels compatibility separately. Missing, skipped or
additional failures block it. E0022's separate formal job qualifies written
compact-executor phase properties and legacy-only refinement, with initial-reset
and explicit fetch assumptions, bounded covers and expected-failing mutants.
E0023 adds the actual compact-copy top, real public loader/program/data stores
and synchronizer. Its universal safety job assumes only initial chip reset;
guided public-pin completion/abort jobs state finite schedules and bounds.
Four simulation groups per simulator cover complete image readback, all byte
values, all 40 abort cuts, old-result lifetime and reset ownership. Deliberately
wrong loader-clear expectations and a dropped-store-write mutant must fail
with witnesses. Full SPI and physical qualification remain open; ordinary
production proofs stay attached to production sources.

E0024 uses independent external GPIO/clock/CS and rising-edge word expectations
for the complete public-loaded compact eight-word image. Per-bit original
response and ideal digital aperture/noise envelopes remain distinct from
electrical timing. Separate formal jobs qualify only the actual synchronizer
with an independent schedule monitor; full-program SAT attempts remain
inconclusive. Retain profile/masking, early-firmware and interruption controls,
case manifests and representative timestamped public traces. Agreement between
simulators and the transport proof does not turn those attempts into passes.

E0025 adds one depth12/180s actual-program induction configuration. Original
public loading, firmware, timing premise and public assertions are preserved;
loaded-image and per-loop facts are proved strengthening assertions over real
DUT readouts, with no added assumptions. Retain four finite Icarus witnesses
and label them separately from formal covers. Audit generated module state,
assumption sites and inverse readout transforms so that monitor-only or
internally assumed behavior cannot masquerade as the actual-program result.
