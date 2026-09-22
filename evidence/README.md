# Evidence index

| ID | Question | Result | Record |
|---|---|---|---|
| E0001 | Is the bootstrap structurally consistent and ready for a tool-equipped runner? | Static checks pass; RTL and synthesis blocked by missing tools | `E0001-bootstrap/README.md` |
| E0002 | Does the baseline pass on a tool-equipped CI runner? | Static, RTL and generic synthesis PASS; docs PASS | `E0002-ci/README.md` |

Run `make evidence` for new local observations. It creates an isolated run
directory under `build/evidence/` and returns nonzero if any stage fails or is
blocked. Promote small, relevant records here; keep large artifacts externally
with source revision, artifact ID and SHA-256. Preserve previous failures.
