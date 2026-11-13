<!-- Modified from the Tiny Tapeout template README, 2026-09-22. -->
# Protocol Emulator ASIC

**What is the smallest computational substrate that can efficiently express
useful digital communication protocols under hard temporal constraints?**

A research and build project for the Jane Street Protocol Emulator ASIC
Competition. **Deadline: 18 January 2027.** The intended design is a compact,
reprogrammable temporal machine. Its architecture is still a hypothesis.

The project has an equal learning goal: by completion, its owner should be able
to operate, question and defend the complete RTL-to-GDS workflow. Start with
the [project goal](docs/goal.md), the [six execution goals](docs/goals.md) and the visual
[Verilog-to-chip map](docs/learning/map.md); unfamiliar terms are grounded in
the project [glossary](docs/learning/glossary.md).

**Engineering: G1-G3 complete, G4 queued; learning: M0 teach-back pending.**
Production now uses the qualified `od128-sram` temporal engine: 128 logical
program words, one 8,192-bit physical SRAM and 353 register bits. Publicly
loaded programs implement UART TX and bounded RX, both bit orders of all four
SPI modes, and Standard-mode 100 kHz I2C on this same core. Both complete RTL
suites and source-matched formal gates pass in [E0042](evidence/E0042-sram-prefetch-screen/README.md)
and [E0044](evidence/E0044-sram-current-verification/ci-13660ac/README.md).
[E0045](evidence/E0045-g2-sram-qualification/README.md) verifies the fresh pinned
8x4 GDS, timing, ten prechecks and eighteen actual-netlist public test groups.
[D48](docs/decisions/0048-adopt-qualified-sram-production.md) binds adoption to
the exact qualified files. [Clean default-command CI](evidence/E0045-g2-sram-qualification/ci-default-75c1e7d/README.md)
passes all eight stages on the actual production source; its original archive
and frozen replay pass. [Alpha.6](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.6)
publishes the qualified milestone with verified downloads, matching tools image
and all eight tag workflows passing. The [completion audit](evidence/E0045-g2-sram-qualification/completion-audit.json)
closes G2; [state](docs/state.md) identifies the next work.

The [programming guide](docs/programming.md) explains G3's readable assembler,
timing listings and public load/readback plans. `workbench.ps1 Programs` builds
the versioned examples; `workbench.ps1 ProgramTest` checks their public-pin
execution in both simulators using the independent protocol oracles.
[Alpha.7](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.7)
publishes the standalone assembler and thirteen examples with verified public
downloads and a matching workbench image. [E0046](evidence/E0046-program-toolchain/README.md)
retains clean-checkout qualification and the completed publication audit.

Interface **0x22** requires one rising edge for program-byte readback; see the
[production profile](docs/specs/g2-production-profile.md). UART retains its
framing, phase and bounded host-service/delivery limits. SPI requires its
declared input hold; edge-only failures remain expected controls. I2C retains
external pull-up/resolved-bus assumptions, stretching and bounded cleanup.
Continuous autonomous UART, broad peripheral interoperability, analog bus
qualification and fabricated-silicon results remain open.

The earlier isolated compact SPI candidate has a formal proof for its eight-word
mode0/2 programs, both bit orders and symbolic payloads under an explicit
input-hold requirement ([E0028](evidence/E0028-held-program-induction/README.md)).
The subsequent timed post-action GPIO P candidate fits modes1/3 into eight
words and passes its scoped proof and public-pin comparison
([E0030](evidence/E0030-timed-gpio-comparison/README.md)). It uses 3,146 generic
cells/412 state bits against matched compact10's 3,589/477. This is not mapped
area or physical timing evidence, and it has not replaced production RTL.
The matched physical comparison now selects **compact10** as the experimental
pilot: GDS, routed metrics, ten prechecks and twelve public netlist test groups
pass under the frozen 8x4/20 ns setup. P uses 13.1456% less routed standard-cell
area but fails a fanout limit. [D35](docs/decisions/0035-select-compact10-physical-pilot.md)
and [E0031](evidence/E0031-8x4-physical-comparison/README.md) retain the results
and limits. G2's later SRAM adoption preserves this G1 qualification and the
rejected P result; the production source and physical setup are separately
bound to E0045.

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

## Releases and packages

[Versioned research releases](https://github.com/KG-khangelani/protocol-emulator-asic/releases)
and the
[verification workbench package](https://github.com/KG-khangelani/protocol-emulator-asic/pkgs/container/protocol-emulator-asic-workbench)
are maintained by the [publication workflow](.github/workflows/publish.yaml).
See [how releases and packages are updated](docs/releases.md) for checks,
versioning and container use. Research prereleases retain the qualification
limits above.

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

The Protocol atlas is independent of Docker/EDA. With Node 24
and Python 3 for the independent model checks:

```powershell
cd web
npm ci --ignore-scripts
npm test
npm run build
npm run dev
```

Open `http://127.0.0.1:5179`. The server binds to loopback only.
On KhanCreate, the repo-root shortcut is `.\tools\atlas.ps1 Start`: it builds
the checked snapshot and serves it locally. Stop with Ctrl+C; no Docker,
execution-policy change, global install or port-killing is involved.
The checked-in dataset is regenerated with `npm run data` and checked against repository source
by `npm run data:check`. No API key, device connection or telemetry is used.
Browser verification uses pinned Playwright/Chromium; see [web/README.md](web/README.md).
The app is integrated through PR9 and is not deployed to GitHub Pages.

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

`make evidence` checks the current source, models, runtime and retained stage
files before reusing completed results. It runs missing/invalid stages, reruns
repository consistency checks, and writes `build/current/evidence.json` with
the source-bound receipts and logs. The historical eight-word profile retains
its separate `build/evidence/<timestamp>/` collector. M0 learning commands stay
on their archived source. Missing required tools produce a nonzero exit;
generic Yosys synthesis does not establish IHP area or timing.

Linux/WSL users can run equivalent commands with `./tools/workbench.sh`. Native
tools remain useful for exploration, but the locked workbench is the reproducible
local acceptance path. The official GitHub CMOS5L workflow remains the authority
for physical fit and timing; a local generic synthesis pass cannot replace it.

## Project map

| Location | Purpose |
|---|---|
| `AGENTS.md` | Codex working rules and verification boundaries |
| `docs/goal.md` | Equal technical and fluency outcomes |
| `docs/goals.md` | Prioritized goals, completion checks and planning targets |
| `docs/state.md`, `docs/backlog.md` | Persistent state and next executable tasks |
| `docs/learning/` | Practical map, glossary, labs, checkpoints and conservative fluency status |
| `docs/specs/m0-gpio.md` | Exact pin-level baseline behavior |
| `docs/specs/protocol-atlas.md` | Approved UI direction and source/interaction/verification contract; implementation tracked separately |
| `src/` | Qualified production RTL, memory declaration and physical configuration |
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
