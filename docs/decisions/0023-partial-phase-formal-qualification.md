# D23 - Qualify written phase properties without promoting production RTL

Date: 2026-11-03. Status: bounded engineering slice, partial executor evidence.

Formal verification searches allowed digital input sequences for violations of
written properties. K-induction establishes those properties beyond the finite
base prefix; covers demonstrate reachable examples. Deliberately faulty variants
check whether the assertions detect specific errors. These are different kinds
of evidence and must retain their actual outcomes.

Extend D22 with an isolated compact-executor harness and a paired comparison
against the unchanged production executor. Freeze assumptions and obligations
in [the formal contract](../specs/spi-phase-formal.md). The only safety input
assumption is reset on the first sampled edge. Afterwards instructions, valid,
enable, reset, input bits and both payloads vary freely. Keep the delay at its
full 16-bit width; prove decrement/capture rules rather than shrinking it for
the solver. Indefinite stalls/reset remain possible, so no wall-clock liveness
claim follows.

For legacy refinement only, exclude the two newly allocated phase types at an
enabled valid RUN fetch in the reference engine. Every previously legal opcode
remains admitted, and ignored-cycle instructions remain unrestricted. Compare
all shared engine state/status and GPIO/result outputs. This preserves prior
legacy-only behavior from reset; it does not turn the old engine into a golden
implementation of the new extension or prove a complete public-pin program.

Expose the two phase flags through formal-only output wires and a module rename.
Mechanically invert that instrumentation and require byte-identical candidate
source recovery. Add no DUT input, register, clock or functional logic. Production
and uninstrumented candidate hashes remain identical to E0021.

The first induction attempt starts in an unreachable RUN state with shift
period1 and clear phase flags. Its 24-step base check passes but induction is
UNKNOWN. Add nonzero-period-implies-WAIT as an assertion, not an assumption on
inputs or internal state. A separate runner failure exposes the installed SBY
status format `PASS 0 <time>`; validate its optional numeric fields while
retaining the complete raw status. Do not rewrite either failure as a pass.

Keep the successful proof, cover and expected mutation-failure records separate
in E0022. No candidate fix is warranted by these results. Preserve the original
coupled-SPI counterexample and E0021's banked-loader compatibility failure.
The new job remains separate from production `make formal` in CI.

Next, check compact-copy integration of the actual result store and public
loader/reset abort path. This slice is not a new integrated top-level proof,
four-mode/continuous SPI qualification, electrical/physical timing result or
production-readiness decision. Keep PR11 draft/unmerged, production RTL and
visualizer unchanged, PR8/compiler deferred and M0 owner fluency PENDING.
