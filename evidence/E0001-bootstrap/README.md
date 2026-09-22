# E0001 — Repository bootstrap

Date: 2026-09-22. Question: is the M0 scaffold internally consistent and ready
to execute on a runner with the HDL dependencies?

Commands: `make doctor`, `make check`, `make evidence`, `git diff --check`.
The machine-generated `manifest.json` identifies the source revision, dirty
state where applicable, input hashes, tool availability and stage outcomes.
Each stage has its own log.

Observed: repository consistency checks pass. Icarus, cocotb and Yosys are
missing, so RTL and generic-synthesis stages are explicitly **BLOCKED**. Docker
is absent; the CMOS5L physical flow has not run. No waveform, mapped area,
timing report, gate-level pass, GDS or formal proof is claimed.

Independent inspection: all 22 template files were verified against their
upstream Git blob hashes before import. This is provenance evidence, not HDL
correctness evidence.

Next: execute CI on the project remote, then the official GDS workflow; retain
actual results and resolve failures before changing the M0 completion state.
