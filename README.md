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

**Engineering: M1 reloadable sequencer; learning: M0 teach-back pending.** The
repo implements a public-pin-loaded temporal engine, synchronized bounded input
waits, LOOP and reusable shifting. Named digital UART transmit and bounded
last-byte receive workloads have RTL/scoped-formal qualification; see
[E0016](evidence/E0016-uart-tx-8n1/README.md) and
[E0018](evidence/E0018-uart-rx-public/README.md). This is not continuous/full UART,
SPI/I2C, M1 physical fit/timing or silicon evidence. The separate
[PR8 host-service candidate](https://github.com/KG-khangelani/protocol-emulator-asic/pull/8)
remains draft/unmerged, not part of main.

The archived deterministic GPIO M0 has passed its pinned CMOS5L GDS,
gate-level, precheck and clean-rerun gate ([E0010](evidence/E0010-pinned-cmos5l-run/README.md)).
Its owner fluency gate remains pending; **M0 is not complete**. Engineering
progresses independently without automatically promoting human understanding.
Current task and exact claim boundaries are in [docs/state.md](docs/state.md).

The [Protocol atlas contract](docs/specs/protocol-atlas.md) records neutral,
compact, source-backed architecture/cycle/evidence views and sparing relationship
tracing. Its direction is approved, including dark mode, softer surfaces and
fewer borders. The first working [browser app](web/) now provides architecture,
reference cycles, evidence and progress views. It runs locally, not on a chip;
[UI0001](evidence/UI0001-protocol-atlas/README.md) records scoped browser/model
checks and limits. Implementation continues as reviewable increments.
Private concept/reference images are not published.

## Start with Codex

Open this repository's root folder in Codex. The root [AGENTS.md](AGENTS.md)
provides project instructions; [docs/state.md](docs/state.md) identifies the
current task and blockers. Use this first task:

> Read AGENTS.md, docs/state.md and docs/backlog.md. Inspect local and remote
> heads; preserve unrelated work. Run Doctor and checks relevant to the active
> scoped change. Keep engineering qualification separate from M0 owner learning;
> do not rerun archived physical closure merely to report progress. Record
> evidence and push coherent reviewable increments. Implement the approved
> visualization contract without another concept round; do not infer merge,
> hardware-spend or competition-submission permission from commit/push permission.

No API key or agent-specific model setting is needed in the repository.

## Run locally

The Protocol atlas is independent of Docker/EDA. With Node 24 (minimum 22.12)
and Python 3 for the independent model checks:

```powershell
cd web
npm ci --ignore-scripts
npm test
npm run build
npm run dev
```

Open `http://127.0.0.1:5179`. The server binds to loopback only. The checked-in
dataset is regenerated with `npm run data` and checked against repository source
by `npm run data:check`. No API key, device connection or telemetry is used.
Browser verification uses pinned Playwright/Chromium; see [web/README.md](web/README.md).
The app is not deployed to GitHub Pages and this branch is not merged.

The supported Windows path needs Docker Desktop, PowerShell and Git; chip tools
run inside the pinned Linux workbench:

```powershell
.\tools\workbench.ps1 Setup
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 LearnStatus
.\tools\workbench.ps1 LearnM0
.\tools\workbench.ps1 LearnWaveform
.\tools\workbench.ps1 All
```

`Setup` builds the sealed tool environment, `Doctor` explains every tool and
rejects version drift, and `All` runs consistency checks, Verible lint, the
active cocotb regression through Icarus and Verilator, scoped engine/storage/
synchronizer formal proof/covers/mutation, and generic Yosys synthesis. Individual
commands include `Check`, `Lint`, `Test`, `TestVerilator`, `Formal`, `Synth`,
`Evidence`, `LearnStatus`, `LearnM0`, `LearnWaveform`, and `Shell`. `LearnStatus`
shows technical and human gates separately and never promotes understanding from
CI alone. `LearnM0` is a read-only,
evidence-backed tour; add `Physical` as its second argument to focus on
synthesis-to-GDS. `LearnWaveform` reruns the M0 Icarus test in readable VCD mode
and prints the reset, count, wrap, hold, resume and reset-priority edges.

`make evidence` reruns the verification stages, including conservative learning-
status validation and the readable waveform walkthrough, and writes logs plus a
machine-readable manifest under
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
| `docs/learning/` | Practical map, glossary, labs, checkpoints and conservative fluency status |
| `docs/specs/m0-gpio.md` | Exact pin-level baseline behavior |
| `docs/specs/protocol-atlas.md` | Approved UI direction and source/interaction/verification contract; implementation tracked separately |
| `src/` | Synthesizable Verilog and preserved physical configuration |
| `web/` | Local source-backed interactive atlas, not device control |
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
