# Current state

Updated: 2026-09-25. Phase: **M0 — physical-flow closure**.
Hard deadline: **2027-01-18**. Active task: **M0-T01**, [GitHub issue #1](https://github.com/KG-khangelani/protocol-emulator-asic/issues/1).

Research question: What is the smallest computational substrate that can
efficiently express useful digital communication protocols under hard temporal constraints?

## Established

- Official CMOS5L template retrieved; all 22 imported file blobs verified.
- Local Git `main` initialized with template import history.
- Public GitHub repository released after E0004 audit: https://github.com/KG-khangelani/protocol-emulator-asic
- Codex instructions, specifications, ledger, backlog and reproducibility commands created.
- M0 GPIO counter, cocotb tests and CI prepared.
- Local static checks pass; see `evidence/E0001-bootstrap/`.
- GitHub CI passed static, GPIO RTL regression, generic synthesis and docs build;
  see `evidence/E0002-ci/` for the tested source revision and result links.
- The E0002 CI ZIP is durably archived in the repository with a matching
  GitHub-reported SHA-256.
- Publication controls are enabled: GitHub secret scanning, push protection,
  Dependabot security updates and private vulnerability reporting.
- Docker Desktop is available locally. The project Python environment passes
  static checks; native Windows `make`, Icarus and Yosys remain absent.
- A locked Linux/amd64 Docker workbench provides exact-version checks, Verible
  lint, simulation and generic Yosys synthesis from Windows. E0005 records its
  initial Icarus validation; the current candidate also passes the same two
  tests locally with Verilator.
- The first official CMOS5L run produced a GDS, positive setup/hold slack,
  zero reported route/Magic DRC and LVS errors, and passed every Tiny Tapeout
  precheck. See `evidence/E0003-cmos5l-first-run/`.
- The missing gate-level UDP model was added to `test/Makefile`; the exact E0003
  netlist now passes locally. Corrected official run 36111852179 passes GDS,
  gate-level regression and every precheck.
- GitHub now reports the pytest Dependabot alert as fixed after dependency-graph
  refresh recognized pytest 9.0.3; it was not manually dismissed.

## Blocked or unverified

- The physical workflow still names a mutable upstream branch even though
  E0003 records the resolved action, flow and PDK revisions. Pin successful
  inputs after the passing rerun.
- The candidate fast GitHub workflow now builds the same lock and runs both
  Icarus and Verilator, but its first remote result is pending. M0 formal
  properties are not wired in.
- No clean pinned physical rerun, FPGA run or devcontainer validation exists
  yet. Positive slack at the 20 ns target is not a measured maximum frequency.

## Next executable action

Validate the locked fast workflow on GitHub and add the M0 formal harness.
Archive corrected physical run 36111852179, pin its resolved workflow inputs,
and require a second clean run before declaring M0 complete.

## Handoff boundaries

M0 is **in progress**, not completed. No VM, protocol firmware, compiler, formal
proof or physical-fit claim exists yet. The original OpenKnowledge records
named in `source-pack.md` were not modified or synchronized by this setup.
