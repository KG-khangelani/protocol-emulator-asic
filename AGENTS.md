# Protocol Emulator ASIC — agent instructions

Research question: **What is the smallest computational substrate that can
efficiently express useful digital communication protocols under hard temporal constraints?**

Hard deadline: **18 January 2027**. Work toward an open-source, reprogrammable
ASIC for Jane Street's competition. Start with UART, SPI and I2C; USB low-speed
and 10 Mbit Ethernet are stretch goals. The temporal VM is a hypothesis.

## Start every session

1. Read `docs/state.md`, then the active task in `docs/backlog.md`.
2. Read the relevant specification under `docs/specs/` before changing RTL.
3. Inspect `git status`; preserve unrelated work.
4. Run `make doctor` and the checks needed for the change.

## Work loop

Formalize → execute → attempt to falsify → measure → record → converge.
Keep verified facts, hypotheses, decisions, results, open questions and rejected
approaches distinct. Link architectural claims to inspectable evidence.
AI-generated explanations are not proofs. Failed or unavailable tools are not passes.

## Commands

- `make setup`: install Python verification dependencies into `.venv`.
- `make doctor`: report tools without installing anything.
- `make check`: validate metadata, source list, clocks and Python syntax.
- `make test`: cycle-level RTL regression using Icarus and cocotb.
- `make synth`: generic Yosys sanity synthesis; NOT IHP area or timing evidence.
- `make evidence`: execute checks and record versions, source hashes and results.
- `.github/workflows/gds.yaml`: official CMOS5L hardening, precheck and gate-level test.

## Implementation constraints

- Preserve the official Tiny Tapeout interface and `src/config.json` unless a
  documented, evidence-backed change is needed. `info.yaml` uses **6x4** tiles.
- M0 is a deterministic GPIO counter, not a protocol VM. Close the physical-flow
  gate before broadening the architecture; draft M1 semantics separately.
- Use synthesizable Verilog, explicit widths, nonblocking clocked assignments,
  and `default_nettype none`. No inferred latches or internally generated clocks.
- Define reset, enable, latency, pin direction and timing at the specification level.
- Test observable behavior against independent expectations; retain failing seeds.
- Synchronizers, open-drain behavior, contention and bounded external waits must
  be specified before protocol input/output is implemented.
- A 50 MHz clock constraint is a target, not a demonstrated maximum frequency.
- Never mark M0 complete without GDS, timing/area, precheck and clean rerun evidence.
- Keep generated bulk output under ignored `build/` or `runs/`; retain curated,
  small evidence under `evidence/`. Do not commit credentials or PDK bulk data.

## Finish a task

Update `docs/state.md` and the relevant backlog row. Record meaningful decisions
in `docs/decisions/`, experiments in `evidence/`, and affected claims in the
research ledger. Report exactly what ran, what failed or was blocked, and the
next executable action. Commit cohesive changes when requested or part of setup.
Do not rewrite historical failed evidence to make a result look successful.
