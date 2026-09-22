# D1 — Bootstrap from the official CMOS5L template

Date: 2026-09-22. Status: adopted for M0.

Need: establish a small reproducible hardware build and a persistent Codex
work context before making architecture claims.

Decision: preserve the official template as the first local commit and retain
its Apache-2.0 license. Adapt the top and tests to an 8-bit deterministic GPIO
counter. Keep the flow's 20 ns target and set the competition's 6x4 allocation.
Use Verilog plus the template's cocotb/Icarus harness; retain CMOS5L GDS actions.
This does not choose the final VM ISA, storage, clock rate or protocol loading path.

Explicit changes from upstream:

- Replace example adder/top/test/datasheet with the M0 contract.
- Make simulation paths robust under `make -C test`.
- Extend CI with static checks, generic synthesis and evidence capture.
- Trigger GDS manually; leave the Pages viewer disabled until configured.
- Align the devcontainer PDK variable with the CMOS5L workflow and add Yosys.
- Add research state, agent instructions, provenance and curated evidence.

Tradeoff: initial workflow action refs and several container dependencies remain
mutable, matching upstream. Template provenance is pinned but the complete
physical toolchain is not yet locked. M0 must record and stabilize those inputs.

Rejected for this step: broad ISA implementation before the toolchain has any
physical evidence. This is a sequencing decision, not a falsification of the VM.
