# Waveform provenance correction

Date: 2026-10-03. Scope: M1-T08 evidence integrity only.

## Finding

On merged `main` at `b3b73e6fc63b2b22c9f9bd2314fd9e7a97b6266a`, the
GL-shaped harness smoke ran after the full Icarus regression and reused
`test/tb.fst`. The resulting 1,548-byte file represented the 11 ns reset smoke,
but the evidence collector associated it with `rtl_icarus`. The separate JUnit
files still accurately reported eight full tests and one smoke test.

## Correction and falsification

The smoke now dumps `test/tb-gl-harness.fst`; `test/tb.fst` remains the full
regression path and the official `GATES=yes` convention remains unchanged. A
new provenance check snapshots the full waveform/JUnit hashes before the smoke,
then verifies both hashes are unchanged, both waveforms are nonempty and
different, and JUnit modules agree with the `rtl_icarus` and
`gl_harness_smoke` labels.

Three unit tests exercise the valid mapping, deliberately overwrite the full
waveform after its checkpoint, and deliberately apply the smoke module label to
the full result. Both corrupt cases are rejected.

## Local result

The focused locked-workbench run passes eight full Icarus cases over 15,465 ns
and one GL-shaped smoke case over 11 ns. It retains a 5,388-byte full FST and a
1,549-byte smoke FST with distinct SHA-256 values in
`build/waveform-provenance.json`. Static checks and all 16 specification/unit
checks pass. The complete evidence collector also passes all 11 stages: doctor,
static consistency, learning-status integrity, lint, both separated Icarus
stages, waveform provenance, the readable learning waveform, Verilator, formal
verification, and generic synthesis. Exact-head CI and independent review are
pending.

This repairs simulation evidence provenance only. No RTL behavior, instruction
semantics, physical flow, gate netlist, timing result, owner-fluency status, or
competition submission is changed. K-SHIFT-8 work remains out of scope.
