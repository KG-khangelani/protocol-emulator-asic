# E0014 — Docker-independent M0 lesson qualification

Question: **Can a clean Windows checkout run the evidence-reading M0 lessons
without invoking Docker, while the locked EDA regression remains green?**

GitHub test run [36174849025](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36174849025)
tested commit `010fb2eb9e4ec2a436cf5932f368b128f3e1e487` on 25 September
2026. The companion [docs run 36174849038](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36174849038)
also passed.

## Why this exists

The Docker image is the reproducible workshop for commands that execute EDA
tools. `LearnStatus` and `LearnM0` only read committed evidence with the Python
standard library. Making those two reading lessons wait for Docker unnecessarily
coupled the project's fluency outcome to the host container runtime.

Decision 0007 keeps the boundary narrow: the PowerShell wrapper prefers host
Python only for these two read-only lessons and falls back to Docker when host
Python is unavailable. Simulation, waveform generation, lint, formal proof and
synthesis remain in the locked container.

## What passed

| Observation | Result |
|---|---|
| Clean Windows checkout of the exact source revision | PASS |
| `workbench.ps1 LearnStatus` selected `HOST LEARNING MODE` | PASS |
| Status output kept M0 technical `PASS` and fluency `PENDING` | PASS |
| `workbench.ps1 LearnM0 RTL` selected `HOST LEARNING MODE` | PASS |
| RTL lesson defined `rst_n` and worked the `ena=0` hold row | PASS |
| Locked Linux doctor/static/status/lint/simulations/waveform/formal/synthesis ladder | 9/9 PASS |
| Verification artifact upload | PASS |
| Windows, Linux and docs job annotations | 0 |
| Documentation build | PASS |

The Windows job has only checkout and lesson steps; it contains no Docker or EDA
invocation. `windows-learning.log` retains the relevant output rather than the
credential-redacted checkout boilerplate. `remote-manifest.json` records the
job, runner-image, source, artifact and source-file identities. The downloaded
verification artifact independently records a clean Git status at the same
source revision and the unchanged locked workbench image ID.

## Claim boundary

E0014 proves that these two versions of the read-only scripts and PowerShell
wrapper ran from a clean Windows checkout without asking Docker to execute, and
that the existing containerized verification ladder still passed. It does not
prove that host Python is an EDA environment, that every Windows installation
will expose a usable `python` command, or that Docker is unnecessary for chip
work. It does not demonstrate owner understanding, repair the current host's
Docker Desktop runtime, change RTL, or add protocol, physical, analog, FPGA or
silicon evidence.
