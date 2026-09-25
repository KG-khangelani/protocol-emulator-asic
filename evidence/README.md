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
| E0008 | Can a read-only monitor detect upstream action-ref drift without altering qualification pins? | Initial remote canary PASS; live and qualified commits CURRENT and equal | `E0008-upstream-canary/README.md` |
| E0009 | Can a fresh Windows clone run the locked ladder without native EDA and read the same physical-input bytes as Linux CI? | All 7 stages PASS; native EDA commands absent; compared SHA-256 values identical | `E0009-fresh-windows-clone/README.md` |
| E0010 | Does a clean run of the repository-pinned CMOS5L flow reproduce the complete physical result? | GDS, 2 gate-level tests, and all 9 prechecks PASS; E0006 metrics and non-timestamp GDS records reproduced | `E0010-pinned-cmos5l-run/README.md` |
| E0011 | Do immutable Node 24 Docker actions preserve the locked fast-CI result and remove the Node 20 warning? | All 7 stages and artifact upload PASS; 0 check annotations; locked image identity unchanged | `E0011-node24-fast-ci/README.md` |
| E0012 | Can a clean GitHub checkout run the beginner-readable M0 waveform lab, check every rising edge, and reject a corrupted transition? | 2 tests and all 1,561 edges PASS; intentional corruption rejected; docs PASS | `E0012-readable-waveform-ci/README.md` |

Run `make evidence` for new local observations. It creates an isolated run
directory under `build/evidence/` and returns nonzero if any stage fails or is
blocked. Promote small, relevant records here; keep large artifacts externally
with source revision, artifact ID and SHA-256. Preserve previous failures.
