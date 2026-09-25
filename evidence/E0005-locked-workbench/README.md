# E0005 — Locked developer workbench

Question: can a Windows user run the project's fast open-source EDA checks in
one version-checked Linux environment without native Windows chip tools?

## Result

**PASS** for the workbench identity, static consistency, Verible lint, the
Icarus/cocotb M0 regression, and generic Yosys synthesis at source commit
`44f77d399437e7d9d5a31a305b9ccdb7bf87276a` with a clean Git status.

**NOT_EVALUATED** for formal verification: `make formal` deliberately exited 2
and named the missing M0 property harness. **NOT_EVALUATED** for physical fit:
this workbench does not replace the official CMOS5L flow.

## Reproduce

From the repository root on Windows with Docker Desktop running:

```powershell
.\tools\workbench.ps1 Setup
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 All
.\tools\workbench.ps1 Evidence
```

The evidence collector ran at `2026-09-25T08:56:26.892305Z`. Its three executed
stages—static, RTL, and generic synthesis—passed. A separate exact-commit
`Doctor` and `Lint` rerun also passed. The observed local OCI image digest was
`sha256:73613a54eb186b6af58c0e9158faca611595c76435e6da0828a90076d9f77f5d`.

## What was observed

| Check | Result | Visible observation |
|---|---|---|
| Strict doctor | PASS | Every required tool, package, platform marker and lock hash matched |
| Repository consistency | PASS | Metadata, pins, source list, top, clock and parsed project files agree |
| Verible lint | PASS | Default rules pass with the documented Tiny Tapeout filename waiver |
| RTL simulation | PASS | 2 tests pass: reset/count/wrap/hold/resume plus seeded input noise |
| Generic synthesis | PASS | 22 generic cells; Yosys `check` reports 0 problems |
| Formal | NOT_EVALUATED | Property harness not yet present; exit status 2 is intentional |
| CMOS5L physical fit | NOT_EVALUATED | Must be established by the official GDS workflow |

The cocotb wheel prints a Python 3.11.9 compile-time banner. Loader tracing
showed that simulation loads `/usr/local/lib/libpython3.11.so.1.0` from the
pinned Python 3.11.16 image; the strict doctor checks that runtime.

## Boundaries

- The local image digest records this build; build metadata can make a later
  digest differ even when all locked inputs are the same.
- Verilator is installed and version-checked, but its independent simulation
  path is not wired into `All` yet.
- Passing two test cases covers those scenarios, not every allowed input trace.
- Generic cells do not establish IHP cell area, routing, timing, DRC, LVS or
  gate-level equivalence.

Machine-readable details and selected artifact hashes are in `result.json`.
