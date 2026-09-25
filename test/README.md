<!-- Modified from the template test instructions, 2026-09-22. -->
# GPIO regression

Run `./tools/workbench.ps1 Test` from the repository root for Icarus, or
`./tools/workbench.ps1 TestVerilator` for the independent Verilator path. The
locked workbench supplies both simulators. Tests use pin observations, never
internal DUT state.

First-time waveform readers can run `./tools/workbench.ps1 LearnWaveform`. It
reruns the Icarus cases as readable VCD, validates all rising-edge transitions,
checks that an intentionally corrupted edge is rejected, and prints selected
events as a table. This is a teaching view of the same finite simulation, not a
third simulator or a physical result.

- `reset_wrap_hold_and_resume`: reset priority, two wraps, pause and resume.
- `seeded_control_and_input_noise`: 1,024 cycles, seed 20260922, sampled control
  variations and between-edge input/control perturbations.

The specification is `../docs/specs/m0-gpio.md`. Icarus writes `results.xml`
and `tb.fst`; Verilator writes `results-verilator.xml`; the learning command
writes `../build/m0-learning.vcd` and `results-learning.xml`. Full waveforms can
be opened using GTKWave or Surfer. Verilator is explicitly given `--timing` so
it implements the testbench's delays instead of guessing. The official CMOS5L
`gl_test` action supplies the gate-level netlist and PDK environment and runs
the same harness using `make GATES=yes`.

The gate-level source order is intentional: the I/O model is followed by
`sg13cmos5l_udp.v`, then `sg13cmos5l_stdcell.v`, and finally the generated
netlist. The UDP file defines low-level sequential truth tables such as
`ihp_dff_r` that are instantiated by the standard-cell model. Omitting it makes
Icarus stop during elaboration before any cocotb test can run.

If running gate-level tests locally, use the current unpowered IHP netlist
path documented by the official hardening guide and provide `PDK_ROOT`.
See `../docs/toolchain.md`. Zero-delay gate-level tests do not validate SDF timing.
