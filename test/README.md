<!-- Modified from the template test instructions, 2026-09-22. -->
# GPIO regression

Run `make setup` and `make test` from the repository root. Icarus Verilog must
be installed separately. Tests use pin observations, never internal DUT state.

- `reset_wrap_hold_and_resume`: reset priority, two wraps, pause and resume.
- `seeded_control_and_input_noise`: 1,024 cycles, seed 20260922, sampled control
  variations and between-edge input/control perturbations.

The specification is `../docs/specs/m0-gpio.md`. Results are `results.xml` and
`tb.fst`; open the waveform using GTKWave or Surfer. The official CMOS5L
`gl_test` action supplies the gate-level netlist and PDK environment and runs
the same harness using `make GATES=yes`.

If running gate-level tests locally, use the current unpowered IHP netlist
path documented by the official hardening guide and provide `PDK_ROOT`.
See `../docs/toolchain.md`. Zero-delay gate-level tests do not validate SDF timing.
