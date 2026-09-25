# Evidence index

| ID | Question | Result | Record |
|---|---|---|---|
| E0001 | Is the bootstrap structurally consistent and ready for a tool-equipped runner? | Static checks pass; RTL and synthesis blocked by missing tools | `E0001-bootstrap/README.md` |
| E0002 | Does the baseline pass on a tool-equipped CI runner? | Static, RTL and generic synthesis PASS; docs PASS | `E0002-ci/README.md` |
| E0003 | Does the M0 baseline pass the official CMOS5L physical and gate-level gates? | GDS and precheck PASS; gate-level compilation FAILS because the UDP model is absent from the source list | `E0003-cmos5l-first-run/README.md` |
| E0004 | Is the repository ready to cross the private-to-public boundary? | History and directory secret scans PASS; license, history, object-size and CI checks PASS | `E0004-publication-audit/README.md` |
| E0005 | Can Windows run the fast checks in one version-verified open EDA environment? | Doctor, static, lint, RTL and generic synthesis PASS; formal and physical are explicitly NOT_EVALUATED | `E0005-locked-workbench/README.md` |
| E0006 | Does the UDP-corrected official CMOS5L run pass every required job? | GDS, 2 gate-level tests, and all 9 prechecks PASS; pinned clean rerun remains required | `E0006-cmos5l-corrected-run/README.md` |
| E0007 | Does clean remote CI reproduce the locked fast ladder and M0 formal proof? | Icarus, Verilator, formal proof/cover/mutation, lint, static, and generic synthesis PASS | `E0007-locked-fast-ci/README.md` |

Run `make evidence` for new local observations. It creates an isolated run
directory under `build/evidence/` and returns nonzero if any stage fails or is
blocked. Promote small, relevant records here; keep large artifacts externally
with source revision, artifact ID and SHA-256. Preserve previous failures.
