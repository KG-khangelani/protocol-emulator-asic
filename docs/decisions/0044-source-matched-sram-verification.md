# D44 - Prepare normal verification for the exact SRAM candidate

Date: 2026-11-12. G2 remains active; production adoption is pending the complete
official physical and actual-netlist artifact audit.

Add an explicit `od128-sram` source profile to the normal verification commands.
It identifies all five E0042 RTL files and both exact vendor digital models,
interface 0x22 and 128 logical words. Unknown source bytes are rejected, and
old-profile receipts or altered SRAM models cannot be reused. Preserve the
historical eight-word profile and D39's separately identified profile.

Use the [SRAM integration contract](../specs/g2-sram-production-integration.md)
for the complete 30-group simulator pair, source-matched formal composition,
current instruction/support properties, historical formal baseline, generic
synthesis and distinct RTL harness waveform. An additional inductive proof
establishes that the actual prefetch output predicts the following registered
program counter under arbitrary inputs. A moving-PC cover passes, and flipping
the prediction's low bit produces a checked mismatch in the actual witness.

Retain two explicit Verible style exceptions on the exact generated engine and
store: standard Verilog `always @*` remains in both combinational blocks. The
unwaived run must report exactly those two warnings; all other files/rules pass.
This preserves the source already undergoing physical qualification. Generic
synthesis reports 3,422 primitive standard-logic cells, 353 state bits and one
real macro black box; its 8,192 physical memory bits are reported separately.
These generic counts are not physical area or timing.

Two formal preparation failures are retained. The first fault injector targets
the older engine's clocked assignment; its new explicit `next-state` mode checks
the exact SRAM engine hash before targeting the corresponding assignment. The
second public-readout preparation cannot resolve the vendor BIST clock mux
through module boundaries. Flattening the actual hierarchy propagates the
existing constant BIST tie-offs and the unchanged full-source proof passes.
No clock, memory model, assertion or design input is replaced or constrained.

The normal lint, synthesis and harness smoke stages and all 116 repository
checks pass. All eleven current SRAM formal stages pass and their actual
proofs, controls, source copies and witnesses pass a semantic replay. The
subsequent historical engine proof hits its unchanged 300-second wall limit;
the combined normal formal stage is incomplete and no aggregate PASS exists.
E0044 retains both preparation failures, that timeout, the exact launch inputs
and later audit code. Its 2,154-file replay passes without accepting the timeout.
Run the complete normal-command CI on this exact source profile. Official
physical qualification, production promotion and publication remain separate gates.
