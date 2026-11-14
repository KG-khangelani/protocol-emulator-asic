# AI use and responsibility

This project was developed with substantial AI assistance through OpenAI
Codex. The owner sets the project direction, priorities and authorization,
including the emphasis on a programmable shared core, retained evidence,
small commits and learning the RTL-to-chip workflow. AI assistance extends
beyond editing prose: it has contributed research and architecture proposals,
RTL, program generators and assembly tools, simulation tests, formal properties,
physical-flow integration, evidence auditors and documentation.

AI agents also run commands, inspect failures and propose or implement revisions
within the authorized work. Parallel agents are used for bounded tasks such
as documentation and independent review when requested. This account does not
attribute every line or claim that the owner manually authored or checked all
generated material. The Git history, decision records and retained experiment
inputs identify the inspectable technical changes.

## How generated work is checked

The project treats generated code and explanations as proposals to test.
Acceptance criteria are written before experiments where practical; successful
execution must be tied to exact source and tool identities. Icarus and Verilator
provide distinct simulator implementations. Protocol oracles inspect public
wire behavior, while formal tools check explicit digital properties. Physical
qualification checks the produced layout and real netlist. Archive audits and
deliberate corruptions test whether evidence can support the recorded claims.

Tests, oracles, properties and auditors can themselves be AI-assisted. Logical
separation between a generator and an oracle reduces shared-implementation
errors, but it is not independent human authorship or certification. Agreement
between tools cannot rule out an incorrect common premise. Property coverage,
external timing assumptions, model limitations and inconclusive attempts stay
visible in [the verification account](verification.md).

## Decisions changed by evidence

The lower-area timed-GPIO P candidate was rejected after a physical fanout
failure. Register-backed program stores failed physical feasibility checks;
SRAM and prefetch were advanced only after separate behavior, mapping and
integration experiments. Early SRAM DRC and power-port failures remain retained
alongside the later passing configuration. The documentation distinguishes
generic counts, mapped cost, routed timing, zero-delay netlist simulation and
actual hardware observations.

AI explanations are not proofs, and a green workflow is not sufficient evidence
on its own. Original artifacts, exact input hashes, failure controls and replay
instructions support review. No fabricated-silicon validation or external human
certification is claimed. The owner's understanding is a separate assessed goal;
successful automation does not complete the pending M0 teach-back.
