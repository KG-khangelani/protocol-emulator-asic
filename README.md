<!-- Modified from the Tiny Tapeout template README, 2026-09-22. -->
# Protocol Emulator ASIC

**What is the smallest computational substrate that can efficiently express
useful digital communication protocols under hard temporal constraints?**

A research and build project for the Jane Street Protocol Emulator ASIC
Competition. **Deadline: 18 January 2027.** The intended design is a compact,
reprogrammable temporal machine. Its architecture is still a hypothesis.

The project has an equal learning goal: by completion, its owner should be able
to operate, question and defend the complete RTL-to-GDS workflow. Start with
the [project goal](docs/goal.md) and the visual
[Verilog-to-chip map](docs/learning/map.md); unfamiliar terms are grounded in
the project [glossary](docs/learning/glossary.md).

**Current state: M0 physical-flow closure.** The repo contains a deterministic
GPIO baseline, pin-level tests, a locked Docker verification workbench, and the
official Tiny Tapeout CMOS5L physical workflow. The first physical run produced
a cleanly checked GDS with positive timing slack, while its separate gate-level
job exposed a missing PDK model in the test source list. That defect is fixed;
the corrected official GDS and gate-level jobs pass, while downstream acceptance
and a clean pinned rerun remain. **M0 is not complete.** No UART, SPI, I2C or VM
is implemented yet.

## Start with Codex

Open this repository's root folder in Codex. The root [AGENTS.md](AGENTS.md)
provides project instructions; [docs/state.md](docs/state.md) identifies the
current task and blockers. Use this first task:

> Read AGENTS.md, docs/state.md and docs/backlog.md. Continue M0-T01. Run the
> GPIO regression and generic synthesis, then the official CMOS5L GDS workflow.
> Record real versions, logs, waveform, physical reports and artifact hashes.
> Keep M0 open until its evidence gates and a clean rerun pass. Do not expand
> the VM instruction set yet.

No API key or agent-specific model setting is needed in the repository.

## Run locally

The supported Windows path needs Docker Desktop, PowerShell and Git; chip tools
run inside the pinned Linux workbench:

```powershell
.\tools\workbench.ps1 Setup
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 All
```

`Setup` builds the sealed tool environment, `Doctor` explains every tool and
rejects version drift, and `All` currently runs consistency checks, Verible
lint, the same cocotb regression through Icarus and Verilator, and generic
Yosys synthesis. Individual commands include `Check`, `Lint`, `Test`,
`TestVerilator`, `Formal`, `Synth`, `Evidence`, and `Shell`.
`Formal` intentionally reports `NOT_EVALUATED` until the M0 property harness is
added in the next verified slice.

`make evidence` writes logs and a machine-readable manifest under
`build/evidence/<timestamp>/`. Missing tools produce **BLOCKED** and a nonzero
exit code. A generic Yosys result does not establish IHP area or timing.

Linux/WSL users can run equivalent commands with `./tools/workbench.sh`. Native
tools remain useful for exploration, but the locked workbench is the reproducible
local acceptance path. The official GitHub CMOS5L workflow remains the authority
for physical fit and timing; a local generic synthesis pass cannot replace it.

## Project map

| Location | Purpose |
|---|---|
| `AGENTS.md` | Codex working rules and verification boundaries |
| `docs/goal.md` | Equal technical and fluency outcomes |
| `docs/state.md`, `docs/backlog.md` | Persistent state and next executable tasks |
| `docs/learning/` | Practical map, glossary, labs and fluency checkpoints |
| `docs/specs/m0-gpio.md` | Exact pin-level baseline behavior |
| `src/` | Synthesizable Verilog and preserved physical configuration |
| `test/` | cocotb RTL and gate-level harness |
| `tools/` | Consistency checks and evidence capture |
| `docs/research-ledger.md` | Hypotheses, questions and falsification gates |
| `docs/decisions/` | Architectural and workflow decisions |
| `evidence/` | Small curated experiment records |
| `.github/workflows/` | Verification, GDS, docs and optional FPGA jobs |
| `CONTRIBUTING.md` | Change, verification and evidence discipline |

## Remote and physical flow

Public repository: https://github.com/KG-khangelani/protocol-emulator-asic

The repository crossed the public boundary only after the E0004 history,
secret, license, object-size and CI audit. Secret scanning, push protection,
Dependabot security updates and private vulnerability reporting are enabled.

The `test` workflow runs on pushes and pull requests. Run `gds` manually once
verification passes; it retains the official CMOS5L build, precheck and
gate-level jobs. The optional Pages viewer is disabled until explicitly
configured. See [docs/toolchain.md](docs/toolchain.md).

## Origin and license

Based on TinyTapeout/ttihp-verilog-template, `cmos5l`, commit
`b86a2a781484bcab7ba522dc5de540086695a430`. All 22 imported files were checked
against upstream Git blob hashes. The first local commit is a verified source
snapshot, not the original upstream Git ancestry. See
[provenance](docs/upstream-template.json) and [sources](docs/sources.md).

Apache-2.0, retaining the template license and source notices. The user-provided
[source pack](docs/source-pack.md) is preserved as project provenance; its
historical local workspace paths are references, not mounted directories.
