# D14: Bind retained waveforms to distinct simulation stages

Status: accepted for the M1-T08 candidate, 2026-10-03.

## Context

`make test` ran the full Icarus regression and then an 11 ns RTL smoke compiled
with the `GL_TEST` harness shape. Both simulations dumped `test/tb.fst`. The
second run therefore replaced the full waveform, while `collect_evidence.py`
copied that path under the `rtl_icarus` stage label.

JUnit results remained separate, so functional pass/fail status was not lost.
The retained waveform identity was nevertheless false and could not support
the label attached to it.

## Decision

- Keep the ordinary and official gate-level default dump path as `test/tb.fst`.
- Give only the local GL-shaped smoke an additional `GL_HARNESS_SMOKE` define
  and the separate path `test/tb-gl-harness.fst`. This avoids changing the
  qualified official `GATES=yes` interface.
- Split evidence collection into `rtl_icarus`, `gl_harness_smoke`, and
  `waveform_provenance` stages.
- Checkpoint the full waveform and JUnit SHA-256 values before the smoke. Fail
  if either changes, if the test modules do not match their labels, if the dump
  paths differ from the declared mapping, or if the two waveforms are equal.
- Retain the provenance JSON and both waveform/JUnit pairs in CI evidence.

## Consequences

The collector can no longer silently label the short harness trace as the full
RTL regression. The check establishes artifact identity and stage association;
it does not establish RTL correctness, gate-netlist equivalence, timing,
physical fit, or fabricated-silicon behavior.
