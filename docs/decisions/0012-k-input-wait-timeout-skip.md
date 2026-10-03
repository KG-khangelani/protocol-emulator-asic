# D12 - Add one-bit timeout skip for K-INPUT-WAIT

Date: 2026-10-03. Status: implemented candidate; local qualification passed.

Decision: assign `WAIT_PIN[25]` as `timeout_skip`. Zero preserves the existing
fail-closed timeout FAULT. One advances PC by two on timeout while an event
advances by one. The three-word kernel in `../specs/k-input-wait.md` uses this
single conditional to mark the event path and reach common HALT on either path.

Reason: the adopted workload requires both paths to halt and be observably
distinct. The previous terminal timeout FAULT could not meet that contract.
This extension adds only the control-flow distinction with a direct workload
witness; a general branch, flags, GET, and loop machinery remain unjustified.

Limit: this establishes no broader branch semantics and does not imply that the
encoding is final. The ablation result is structural: removing timeout skip
makes this exact three-word kernel inexpressible with the current instruction
set. Alternative encodings and denser storage remain measured research tasks.
