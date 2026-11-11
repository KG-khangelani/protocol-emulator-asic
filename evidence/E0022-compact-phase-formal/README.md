# E0022 - Written phase properties and legacy refinement

Observed: 2026-11-03, KhanCreate Windows, existing locked Linux workbench.
Candidate: PR11 prior head `f0c41fcf3aaca14a76dd0c45a23f259599de24fd`.
Rung: **isolated executor formal**, with no production or candidate RTL change.

Formal verification asks whether an allowed digital input sequence can break a
written rule. Induction extends proved transition rules beyond a finite initial
prefix. Covers provide concrete reachable examples. Deliberate mutants test
whether the rules reject specific faulty implementations. Each result applies
to its model, assumptions and written properties.

Here the useful rules are: prepare one bit before sampling it, consume exactly
the requested number of enabled delay edges, assemble RX without changing TX
during SAMPLE, and commit only the valid eighth sample. A separate comparison
checks the existing executor's behavior for prior legal instruction streams.

## Scope and assumptions

The [formal contract](../../docs/specs/spi-phase-formal.md) and
[D23](../../docs/decisions/0023-partial-phase-formal-qualification.md) define the
boundary. Safety assumes **only an initial sampled reset**. Thereafter every
instruction bit, valid, enable, reset, synchronized input bit and both payloads
is symbolic each cycle. No stable program, fixed pin/order, eventual enable,
SPI rate, input response time or fairness is assumed. Counter width remains
16 bits. Assertions establish reachable-state invariants; they are not added
as assumptions to hide bad behavior.

The paired legacy job shares those inputs and reset with the unchanged engine.
At an enabled valid RUN fetch in that reference only, it excludes the two new
manual phase word types (opcode10, bit29=1, bit21=0, mode01/10). Every previous
legal encoding remains admitted; ignored-cycle instructions remain unrestricted.
It compares all shared architectural state/status and GPIO/result outputs.
This is refinement of legacy-only streams from reset. It does not claim that
every formerly invalid word retains its old meaning or that the legacy engine
specifies new phase behavior.

Formal-only output wires expose two phase flags. Instrumentation adds no input,
state or clock; a mechanical inverse recovers the byte-identical uninstrumented
candidate. All five compact candidate file hashes match E0021. Production,
official configuration, visualizer and learning-record hashes are unchanged.

## Final frozen results

All six tasks achieve their required outcomes using SymbiYosys and Z3 4.15.5:

| Task | Configured mode/depth | Actual result | Meaning |
|---|---|---|---|
| Phase properties | prove / 8 | PASS; induction step 6, base steps 0..7 | Written reset/freeze, sequencing, full-width delay, GPIO/shift progression, rejection and result rules hold inductively |
| Legacy refinement | prove / 12 | PASS; induction step 10, base steps 0..11 | Shared executor outputs agree under the declared legacy restriction |
| Phase covers | cover / 40 | PASS; all 10 reached, latest step 25 | Includes byte commit 17 and legacy completion after phase byte 25 |
| Legacy covers | cover / 40 | PASS; all 3 reached by step 17 | Manual commit 9, burst commit 16, alternate payload slot 17 |
| Decrement-by-two mutant | BMC / 8 | **FAIL at step 4**, expected | Rejects pending counter 2 becoming0 instead of 1 |
| Premature sample 7 commit mutant | BMC / 20 | **FAIL at step 14**, expected | Rejects a result pulse with only six prior samples |

The exact phase induction properties include reset priority and register freeze,
prepared/active consistency, positive pending counter and period/state invariants,
valid DRIVE GPIO/TX/RX initialization, latched pin/order/payload progression,
SAMPLE capture and no TX advance, phase-slot preservation, invalid-family fault
and no false result write. The expected write predicate includes legitimate
legacy completions as well as valid phase completion. Invalid current fetch
inputs during a pending wait are ignored rather than treated as an accepted
invalid RUN instruction.

The delay proof establishes load N, decrement once per accepted edge while >1,
hold on disable, and capture at 1 for arbitrary 16-bit N. It does **not** unroll a
65,535-edge completion. A cover reaches pending 65535 and decrement 65534 at step 5.
With arbitrary disable/reset, no eventual or wall-clock completion is promised.
Other covers reach immediate capture 3, pending capture 4, freeze/resume 5,
reset-during-pending 4 and invalid sequencing 2.

The two mutants remain FAIL in the retained records. The supervisor passes
because those failures are required; it also requires witnesses, exact cover
counts, successful induction summaries and strict actual SBY statuses. A
timeout, UNKNOWN, missing witness or unexpected result fails the supervisor.

## Reproduction, witnesses and initial failures

Inside the existing image `protocol-emulator-asic-workbench:2026-07-29`:

```sh
python3 experiments/spi_phase/run_formal.py
```

The final local attempt is `build/spi-phase-formal/attempt-05/`. No image build,
pull, new dependency or storage cleanup ran locally. Doctor verifies the lock;
`make check` passes 35 Python cases and metadata/learning checks. Atlas export
consistency passes. No new local RTL simulation is claimed for the unchanged
candidate; exact-head remote CI runs the existing simulations/comparison too.

[result.json](result.json) records tested/protected hashes, assumptions, exact
task outcomes, artifact hashes and provenance. [run-result.json](run-result.json)
retains generated-source hashes, commands and solver details. [inputs/](inputs/)
contains the exact compiled sources, readout bindings and mutations;
[configs/](configs/) and [logs/](logs/) retain every final job. Logs normalize
LF/trailing whitespace only. Instrumentation patch JSON preserves exact diff
text in its `patch` field. Bulk SMT models and full VCDs remain in build/CI.

[witnesses/](witnesses/) contains selected root signals at every SMT step with
the original VCD hashes/paths. Steps are formal steps, not measured nanoseconds.
[counterexamples/](counterexamples/) retains both final mutants' exact Yosys
witness, SMT constraints and generated testbench. These belong to deliberately
faulty generated variants, not to production or the unmodified candidate.

Two initial failures remain under [failures/](failures/):

- Attempt 01: the 24-step base case checks steps 0..23 successfully, but induction
  is UNKNOWN. The retained induction trace starts at RUN with period1 and clear
  phase flags, outside reset-reachable behavior. Adding nonzero-period-implies-
  WAIT as an **assertion** enables induction; candidate RTL is untouched.
- Attempt 02: the phase proof itself passes, while the runner rejects actual SBY
  status `PASS 0 <time>`. The corrected parser validates optional numeric fields
  and retains the full raw status; it still rejects unknown/error outcomes.

Intermediate attempts 03/04 pass smaller assertion/cover sets. The final attempt
adds full phase-family rejection accounting and exact ten/three cover checks.
No failing reachable candidate trace was found, and no candidate fix was made.

## Limits and next action

This is a partial proof of written executor properties. It assumes already
synchronized digital inputs and an effective reset; it is not a new integrated
loader/store/synchronizer proof, full SPI mode/transaction qualification,
electrical timing, CMOS5L area/slack, Fmax or silicon evidence. The unchanged
top's reset expression gives a conditional connection to loader abort; an
integrated proof remains the next executable action.

Next: prove result-store capture and public loader/reset abort using the actual
compact-copy top, store and data registers. Keep production RTL unchanged and
PR11 draft/unmerged. PR8/compiler remain deferred, H1-H4 unproven and owner M0
fluency PENDING. Earlier SPI and banked-loader counterexamples remain unchanged.
New exact-head CI and artifact audit references are tracked on PR11.
