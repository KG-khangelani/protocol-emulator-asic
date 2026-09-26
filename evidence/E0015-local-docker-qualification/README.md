# E0015 — Local Docker qualification and full M0 workbench run

Question: **With Docker Desktop opened on Windows, can this host run the
project's locked open-EDA workbench and pass the complete local M0 ladder?**

The answer is **yes** for source commit
`4de28fa55aa624c04f36d6a42c5d789795dc2f97`. At
`2026-09-25T22:09:25Z` (`2026-09-26 00:09:25` in Africa/Johannesburg), Docker
Desktop reported `running`, its Linux engine answered normally, the locked
workbench doctor passed every version check, and all nine collected stages
passed.

## Plain-language model

Docker Desktop is the outer workshop door on Windows. The project workbench
image is the sealed tool chest inside it. The door must be opened before the
tools can run. The outer application version and the inner tool versions are
separate: `doctor` compares the actual compiler, simulator, formal-solver and
synthesis versions with the repository lock before we trust a run.

This observation used signed Docker Desktop `4.92.0.240144` with Docker Engine
`29.8.0` on Linux/amd64. The workbench image was
`sha256:b0798eacd16296895e70a6fd32112222bb3cc55ae65f752b567cc0e3f977c1b7`.

## Host-state clarification

The owner clarified that Docker Desktop had simply been closed before this run.
No Docker defect or repair was involved. Earlier diagnostic log lines were not
evidence of an active problem requiring recovery. E0015 therefore begins after
Docker was opened and records an ordinary operational qualification.

Inspection observed signed Docker Desktop 4.92.0 and a healthy Linux engine.
No factory reset, WSL unregister, Docker data-disk change, or project-source
change was needed. The existing Docker data VHDX was present, but inspecting its
contents was outside this experiment.

## Commands and results

```powershell
docker version
docker info
docker desktop status
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 Evidence
```

| Observation | Result |
|---|---|
| Docker Desktop status | `running` |
| Signed installed version | `4.92.0.240144`, valid Docker Inc signature |
| Linux engine | `29.8.0`, Linux/amd64 |
| Workbench exact-version doctor | PASS |
| Repository consistency | PASS |
| Learning-record integrity | PASS |
| Verible lint | PASS |
| Icarus simulation | PASS, 2 tests |
| Readable waveform | PASS, 1,561 rising edges; corrupted edge rejected |
| Verilator simulation | PASS, 2 tests |
| Formal proof/cover/mutant check | PASS |
| Generic Yosys synthesis | PASS |
| Physical flow in this run | NOT RUN |

The collector returned exit code zero and recorded a clean Git status before
running. [`local-run.log`](local-run.log) retains the concise console result;
[`result.json`](result.json) retains exact identities, stage states, selected
source hashes, generated-artifact hashes and limitations.

## Claim boundary

E0015 proves that this Windows host can execute this revision's locked local EDA
lane end to end when Docker Desktop is open. It independently refreshes the
fast M0 result, including the deliberately failing mutant that demonstrates the
formal checks can detect a real error.

It does **not** add a third physical-flow qualification, prove silicon behavior,
prove the Docker data disk's contents, show that Docker starts automatically, or
demonstrate owner fluency. The official E0006/E0010 CMOS5L runs remain the
physical authority, and the M0 teach-back gate remains pending.
