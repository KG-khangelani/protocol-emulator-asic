# Contributing

Start with `docs/goal.md`, `docs/state.md`, the active row in
`docs/backlog.md`, and the relevant specification. The project works by
formalizing a claim, executing a check, trying to falsify it, recording the
result, and only then converging on a decision.

## Change discipline

- Keep each commit cohesive and include the tests or evidence for its claim.
- Do not mix generated PDK, GDS or bulk run output into source commits.
- Never broaden architecture while a prerequisite milestone gate is open.
- Preserve the Tiny Tapeout interface and `src/config.json` unless a documented
  physical result requires a change.
- Retain failing seeds, waveforms and counterexamples when they affect a
  decision.
- Use explicit widths, synthesizable Verilog, nonblocking clocked assignments,
  `default_nettype none`, and no internally generated clocks.
- Do not commit credentials, tokens, `.env` files or proprietary process data.

## Before a commit

Run the checks supported by the current environment. Until the container
workbench is complete, the Windows-safe structural command is:

```powershell
& .\.venv\Scripts\python.exe tools\check_project.py
```

Once available, use `tools/workbench.ps1 evidence` for the full fast gate.
Report missing tools as `BLOCKED`; do not reinterpret them as a pass.

Update `docs/state.md`, the backlog, affected decisions and the research ledger
when a result changes project truth.
