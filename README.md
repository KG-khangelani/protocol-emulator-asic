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

**Current state: M0 scaffold.** The repo contains a deterministic GPIO baseline,
pin-level tests, and the official Tiny Tapeout CMOS5L physical-flow workflow.
GitHub CI passed static checks, the GPIO RTL regression, generic synthesis and
the docs build; see [E0002](evidence/E0002-ci/README.md). The CMOS5L physical
build has not run; **M0 is not complete**. No UART, SPI, I2C or VM
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

Prerequisites: Python 3.11+, Git, GNU Make, Icarus Verilog (`iverilog`, `vvp`),
and Yosys for generic synthesis. The included devcontainer is adapted from the
official template; its container build has not been exercised in this setup.

```sh
make setup
make doctor
make check
make test
make synth
make evidence
```

`make evidence` writes logs and a machine-readable manifest under
`build/evidence/<timestamp>/`. Missing tools produce **BLOCKED** and a nonzero
exit code. A generic Yosys result does not establish IHP area or timing.

For a Debian/Ubuntu development machine, install the native prerequisites with
`sudo apt-get install git make python3-venv iverilog yosys` after updating its
package index. For macOS, use the devcontainer or provide equivalent native
tools. Docker is needed for the local physical flow, not for the RTL tests.

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

Repository: https://github.com/KG-khangelani/protocol-emulator-asic

Created private during bootstrap. The competition submission must be open source;
public release remains a later project step. Clone this repository, open its root
in Codex, and follow the startup task above.

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
