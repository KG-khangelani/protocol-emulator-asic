# Current state

Updated: 2026-09-22. Phase: **M0 — toolchain establishment**.
Hard deadline: **2027-01-18**. Active task: **M0-T01**, [GitHub issue #1](https://github.com/KG-khangelani/protocol-emulator-asic/issues/1).

Research question: What is the smallest computational substrate that can
efficiently express useful digital communication protocols under hard temporal constraints?

## Established

- Official CMOS5L template retrieved; all 22 imported file blobs verified.
- Local Git `main` initialized with template import history.
- Private GitHub repository created: https://github.com/KG-khangelani/protocol-emulator-asic
- Codex instructions, specifications, ledger, backlog and reproducibility commands created.
- M0 GPIO counter, cocotb tests and CI prepared.
- Local static checks pass; see `evidence/E0001-bootstrap/`.
- GitHub CI passed static, GPIO RTL regression, generic synthesis and docs build;
  see `evidence/E0002-ci/` for the tested source revision and result links.

## Blocked or unverified

- Icarus, cocotb, Yosys and Docker are absent in the setup environment.
  Native package installation failed locally. GitHub CI provides the passing
  simulation/synthesis evidence.
- Devcontainer, CMOS5L hardening, precheck, gate-level tests,
  post-route timing/area, GDS and repeatability are unverified.
- The physical workflow retains mutable upstream action refs. Record actual
  tool/action/PDK identities during the first build and pin successful versions.

## Next executable action

Run the manually triggered `gds` workflow for the baseline, inspect build,
precheck and gate-level results, and archive physical evidence. Perform a clean
rerun. Also archive the passing CI artifact before its 21 December expiry.

## Handoff boundaries

M0 is **in progress**, not completed. No VM, protocol firmware, compiler, formal
proof or physical-fit claim exists yet. The original OpenKnowledge records
named in `source-pack.md` were not modified or synchronized by this setup.
