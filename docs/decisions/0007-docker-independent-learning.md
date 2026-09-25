# 0007 — Keep read-only learning available without Docker

Date: 2026-09-25
Status: accepted

## Context

The locked Docker image is the authority for lint, simulation, formal
verification and generic synthesis. `LearnStatus` and `LearnM0`, however, only
read committed JSON, CSV, XML, Verilog and Markdown evidence using the Python
standard library. Requiring Docker to start before those two lessons coupled
human learning to an unrelated host-runtime failure.

That coupling contradicts the project's equal technical and fluency outcomes:
the evidence should remain teachable even when the EDA workshop is temporarily
unavailable.

## Decision

On Windows, `workbench.ps1` prefers a working host `python` command for
`LearnStatus` and `LearnM0`. It prints an explicit `HOST LEARNING MODE` boundary
and runs the same repository scripts. If host Python is unavailable, it falls
back to the locked Docker image.

All commands that execute or regenerate EDA results remain in the locked
container. `LearnWaveform` also remains containerized because it runs the real
Icarus regression rather than merely reading retained evidence.

A `windows-2025` GitHub job runs both host lessons from a clean checkout. The
job proves that the wrapper and committed evidence work together without
starting Docker; it does not prove owner understanding.

## Rejected alternatives

- Require Docker for every command: a host-runtime outage would continue to
  block the learning path without adding integrity to these read-only scripts.
- Duplicate the lessons in PowerShell: two implementations could disagree and
  would increase maintenance and review cost.
- Replace executable lessons with static prose: that would lose the existing
  cross-checks between archived source, metrics, tool locks and result files.

## Consequences

The first lesson is available with the ordinary Python already present on the
Windows host, while the reproducible EDA boundary remains unchanged. Green CI
still cannot promote a human fluency criterion; only reviewed owner reasoning
can do that.
