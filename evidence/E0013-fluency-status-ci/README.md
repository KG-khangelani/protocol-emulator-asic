# E0013 — Conservative fluency-status qualification

Question: **Can a clean CI checkout preserve an auditable learning-gate record
while rejecting an unearned human-fluency PASS?**

GitHub test run [36130223560](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36130223560)
tested commit `7fbb99572b4e38dfce5f4a65a070e781d4bbf0fa` on 25 September
2026. The companion [docs run 36130223559](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36130223559)
also passed.

## Why this exists

The project treats technical completion and owner fluency as equal outcomes,
but they are different kinds of evidence. Automation can prove that files,
commands, tool identities, and gate rules agree. It cannot infer whether a
person understands them.

`docs/learning/progress.json` therefore records technical and fluency gates
separately. Every unshown M0 skill remains `NOT_DEMONSTRATED`; the technical M0
gate is `PASS`, while its fluency gate remains `PENDING`. The public record keeps
criterion outcomes and evidence references, not conversation transcripts.

## What passed

| Observation | Result |
|---|---|
| Clean checkout and source identity | PASS |
| Learning milestone/resource/evidence-reference validation | PASS |
| Deliberately forced unearned active-milestone fluency `PASS` | REJECTED as expected |
| Complete evidence collector | 9/9 stages PASS |
| Fast verification ladder | PASS |
| GitHub check annotations | 0 |
| Documentation build | PASS |

The self-test changes only an in-memory copy of the status record. It tries to
promote the active fluency gate while its skills remain undemonstrated. The same
validator rejects that state and emits the retained `FALSIFICATION: PASS` line
in `learning-status.log`.

`remote-manifest.json` retains the clean source revision, source hashes, tool
versions, and all nine stage outcomes. `workbench-image.json` retains the exact
container identity used by CI. `result.json` provides a compact machine-readable
summary and hashes for these curated files. Source SHA-256 values describe the
canonical LF bytes in the clean Linux checkout and match the committed Git
content; a Windows working tree may display those older files with CRLF endings.

## Claim boundary

E0013 proves that this version of the record validator rejects the deliberately
constructed unearned promotion and that clean CI retains the result. It does
not prove the rubric is pedagogically complete, that every possible invalid
record is rejected, or that the owner understands M0. It changes no RTL and
adds no protocol, physical, analog, FPGA, or silicon evidence. Only an owner
explanation plus follow-up reasoning can advance a human criterion.
