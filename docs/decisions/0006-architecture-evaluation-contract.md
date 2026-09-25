# D6 — Compare complete candidates with one evidence contract

Date: 2026-09-25. Status: adopted before M1 architecture experiments.

Need: established and contemporary projects report different boundaries and
units. A CPU can be quoted without memory, a sequencer without its loader, or an
FPGA result beside an ASIC result. Choosing an architecture from those numbers
would not answer the research question.

Decision: use `research/evaluation-contract.md` for every architecture
experiment. The primary boundary is CHIP_COMPLETE; CORE_ATTRIBUTION is only a
secondary cost breakdown. Every workload receives an execution status, and
every numeric value receives a provenance. Candidates share the same mandatory
microkernels, protocol kernels, interface assumptions, clock target, independent
oracle and evidence ladder.

Architecture selection will first enforce programmability, correctness, bounded
timing and physical-fit gates. Remaining candidates are compared without a
post-hoc weighted score: a candidate may be removed when another is no worse on
all primary metrics and better on at least one under evidence of equal quality.

Consequences:

- Program storage, loading, synchronization and pin machinery cannot disappear
  from the headline area result.
- FPGA LUTs, external kGE reports and IHP µm² remain distinct measurements.
- Early preloaded-memory experiments are allowed but cannot satisfy reload.
- A failure or blocker remains visible and `NOT_EVALUATED` is never a pass.
- The temporal sequencer remains a hypothesis to test, not the selected winner.

Rejected: ranking by upstream README figures, comparing execution cores alone,
selecting the most popular competition architecture, or inventing one weighted
score after results are known.
