# Current state

Updated: 2026-09-25. Phase: **M0 — fluency closure**.
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
- The M0 formal suite locally proves the public-pin reset, count, wrap, hold,
  fixed-output, and ignored-input properties, reaches the wrap in a cover
  witness, and rejects an increment-by-two mutant.
- Locked fast GitHub run 36119276357 independently reproduces the full seven-stage
  ladder on a clean checkout: doctor, static, lint, Icarus, Verilator, formal,
  and generic synthesis all pass. E0007 durably retains the manifest, both JUnit
  results, formal logs, synthesis netlist, tool identities, and limitations.
- The first official CMOS5L run produced a GDS, positive setup/hold slack,
  zero reported route/Magic DRC and LVS errors, and passed every Tiny Tapeout
  precheck. See `evidence/E0003-cmos5l-first-run/`.
- The missing gate-level UDP model was added to `test/Makefile`; corrected
  official run 36111852179 passes GDS, both gate-level tests, and all nine
  prechecks. E0006 retains its metrics, hashes, raw summaries, and limitations.
- E0003 and E0006 have identical physical metrics and GDS geometry records.
  Their whole-file hashes differ because GDS timestamp records changed; this
  distinction is documented rather than reported as byte-for-byte reproduction.
- A scheduled read-only upstream canary reports when Tiny Tapeout's live CMOS5L
  action branch moves without changing the qualified pins. Its first remote run
  reports CURRENT and retains the observation in E0008.
- A fresh public-repository clone on Windows 11 passes the seven-stage locked
  ladder through the PowerShell wrapper with no native EDA commands on PATH.
  E0009 also confirms the physical-input byte hashes match Linux CI after LF
  checkout canonicalization.
- Clean repository-pinned physical run 36118046477 passes GDS generation, both
  gate-level tests, and all nine prechecks. E0010 records the exact source,
  action, support-tools, LibreLane, PDK, job, artifact, and report identities.
- E0006 and E0010 are two complete official physical-flow passes under the same
  resolved environment. Their metrics and 393,577-record GDS structures match;
  their exact GDS hashes differ only in 32 timestamp records. The technical M0
  physical gate is satisfied.
- `workbench.ps1 LearnM0` provides a read-only guided inspection of the archived
  RTL, fast verification, physical evidence, claim boundaries, and teach-back
  prompt. Its verification mode is part of the static check; it cannot mark
  owner fluency automatically.
- Fast CI now pins Node 24-native setup-buildx v4.4.1 and build-push v7.4.0
  release commits. E0011 records a clean seven-stage pass, unchanged locked
  workbench image identity, successful artifact upload, and zero check
  annotations after the Node 20 warning was removed.
- GitHub now reports the pytest Dependabot alert as fixed after dependency-graph
  refresh recognized pytest 9.0.3; it was not manually dismissed.

## Blocked or unverified

- The M0 owner fluency checkpoint has not yet been completed; technical closure
  alone does not satisfy the project's equal learning goal.
- The official composite action's internally tagged dependencies remain a
  recorded trust boundary. The upstream canary reports change but never upgrades
  the qualified environment automatically.
- No FPGA run or devcontainer validation exists yet. These are not M0 acceptance
  gates. Positive slack at the 20 ns target is not a measured maximum frequency.

## Next executable action

Complete the M0 fluency teach-back using the retained source, commands, and
evidence. Then record the checkpoint before advancing to M1 semantics.

## Handoff boundaries

M0's **technical gate has passed**, but M0 remains in progress until its fluency
gate passes. No VM, protocol firmware, compiler, or fabricated-silicon claim
exists yet. The original OpenKnowledge records named in `source-pack.md` were
not modified or synchronized by this setup.
