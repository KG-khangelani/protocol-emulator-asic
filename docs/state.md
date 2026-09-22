# Current state

Updated: 2026-09-22. Phase: **M0 — toolchain establishment**.
Hard deadline: **2027-01-18**. Active task: **M0-T01**.

Research question: What is the smallest computational substrate that can
efficiently express useful digital communication protocols under hard temporal constraints?

## Established

- Official CMOS5L template retrieved; all 22 imported file blobs verified.
- Local Git `main` initialized with template import history.
- Private GitHub repository created: https://github.com/KG-khangelani/protocol-emulator-asic
- Codex instructions, specifications, ledger, backlog and reproducibility commands created.
- M0 GPIO counter, cocotb tests and CI prepared.
- Static repository checks pass; see `evidence/E0001-bootstrap/`.

## Blocked or unverified

- Icarus, cocotb, Yosys and Docker are absent in the setup environment.
  Native package installation failed. No simulation or synthesis pass is claimed.
- Devcontainer, GitHub Actions, CMOS5L hardening, precheck, gate-level tests,
  post-route timing/area, GDS and repeatability are unverified.
- The physical workflow retains mutable upstream action refs. Record actual
  tool/action/PDK identities during the first build and pin successful versions.

## Next executable action

Run `test` on the populated remote and inspect its uploaded evidence. Resolve
any test failure before running the manually triggered `gds` workflow. Archive
the physical evidence, then perform a clean rerun of the same source revision.

## Handoff boundaries

M0 is **in progress**, not completed. No VM, protocol firmware, compiler, formal
proof or physical-fit claim exists yet. The original OpenKnowledge records
named in `source-pack.md` were not modified or synchronized by this setup.
