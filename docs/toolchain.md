# Toolchain and reproduction

The supported development path is the Linux amd64 Docker workbench, invoked
from Windows PowerShell or Linux. The physical chip uses a separate pinned
Tiny Tapeout/LibreLane CMOS5L flow. Passing the developer workbench does not
produce or qualify a layout.

The current production profile is **od128-sram**, interface **0x22**. Normal
commands compile the actual `src/` files with the recorded vendor SRAM models.
[D48](decisions/0048-adopt-qualified-sram-production.md) and
[production-profile.json](../tools/production-profile.json) bind all twenty
adopted physical inputs. P, compact10, earlier register stores and M0 retain
their historical evidence; they are not the default production target.

## Start from a known checkout

Use a clean checkout of the commit named by the evidence or release being
reproduced. Record `git rev-parse HEAD` and `git status --short` before the run.
An update to `main` is a new source identity, even if its hardware files match.
On this Windows workspace, keep checkouts and generated output on H:.

With Docker running, from the repository root:

```powershell
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 All
.\tools\workbench.ps1 Evidence
.\tools\workbench.ps1 ProgramTest
```

On Linux or WSL, use the same actions with `./tools/workbench.sh`. `Setup`
explicitly builds the locked image; the wrappers also build it if it is absent.
`Doctor` checks actual tool output against the lock and rejects missing or
different versions. The wrappers use a local image tag, so a tag name alone
does not identify the actual runtime: retain the image inspection and tool
report with the run, as the CI jobs do.

The [toolchain lock](../tools/workbench/toolchain.lock.json) pins the Python
3.11.16 base image by digest, OSS CAD Suite 2026-07-29 and Verible archives by
SHA-256, Debian package versions, and direct/transitive Python requirements
with hashes. Buildx and build actions are pinned by commit. The published
[workbench package](https://github.com/KG-khangelani/protocol-emulator-asic/pkgs/container/protocol-emulator-asic-workbench)
also has immutable digest references in each verified release record.

## Commands and outputs

| Action | Current production behavior |
|---|---|
| `Doctor` | Check locked tool versions and record runtime identity |
| `Check` | Metadata/source/clock consistency, profile guard, learning-status integrity, model/oracle and assembler tests |
| `Lint` | Verible on actual sources; verify the two exact `always-comb` exceptions in the standard-Verilog engine and SRAM read mux |
| `Test` | Complete 30-group Icarus suite, separate RTL harness smoke and provenance check |
| `TestVerilator` | Complete 30-group Verilator suite with the same protocol contracts |
| `Formal` | Current source-matched SRAM/engine/support/prefetch obligations and a separate ten-task historical baseline |
| `Synth` | Generic Yosys structural checks, actual SRAM black box and register-state count |
| `All` | Doctor, Check, Lint, Test, TestVerilator, Formal and Synth |
| `Evidence` | Validate/collect all eight production stage receipts; always rerun Check and execute other stale or missing stages |
| `Programs` | Build the thirteen versioned examples and compare their frozen reference words |
| `ProgramTest` | Assembler acceptance plus generated load/readback plans and independent protocol observations in both simulators |
| `LearnStatus`, `LearnM0`, `LearnWaveform` | Separate learning tools and historical M0 observations; no automatic promotion of human fluency |

Current normal-stage output is under `build/current/`, with fresh run
directories and receipts binding sources, verification inputs, actual tools
and results. Collection can reuse a matching successful receipt; it cannot
legitimately reuse one for changed inputs. Use a new artifact root when a
wholly fresh normal-command run is needed. Inside the locked container:

```sh
make CURRENT_ARTIFACTS=/workspace/build/my-current-run doctor check lint test test-verilator formal synth evidence
python3 tools/run_program_examples.py --out build/my-program-run
```

Use new output directory names. `ProgramTest` creates fresh output by default.
The full RTL suites retain public trace records; their separate harness smoke
FST is RTL evidence, not a gate-level waveform. The lint exceptions are narrow,
source-bound checks, not a claim that unwaived lint has no findings.

The standard-library assembler also runs directly on Windows with Python 3.11
or newer. This convenience does not replace the container for EDA work. The
read-only `LearnStatus`/`LearnM0` commands similarly prefer host Python on
Windows. [Programming](programming.md) covers the standalone toolchain.

## Rebuild the physical candidate

The manual [.github/workflows/gds.yaml](../.github/workflows/gds.yaml) verifies
the production guard before staging, then requires regenerated physical inputs
to match the adopted files. It builds the actual SRAM production profile; it
has no P/compact10 selection. Those experiments have separate workflows.

1. Commit and push the intended source. Record its full revision and require
   the relevant normal and program-tool checks to pass.
2. Dispatch **Actions -> gds -> Run workflow** for that source's ref, and verify
   the resulting run's actual `head_sha`. Do not infer it from a moving branch.
3. Inspect `gds`, `precheck` and `gl_test` separately. Preserve every failure.
4. Retain the six original archives, API identities and completed job logs.
   Audit source, staged inputs, actual runtime/PDK, layout, netlist and results.
5. Rebuild from a separate clean checkout with the same frozen inputs. Compare
   acceptance, timing/area, netlist, public traces and GDS records. Timestamp-only
   equality and different-but-passing geometry are distinct outcomes.

The flow uses Tiny Tapeout action
`5e7361fdc445649261c0725dc15f38242dfad330`, support tools
`9d13ff3e3e6202090740110438c6a10c1d62ca0f`, LibreLane `3.1.0.dev4`, and IHP PDK
`89d42ee6d2fd9b50b86a1aada6fee6673c3e6008`, with the actual immutable image
recorded in the workflow and run logs. The process is **ihp-sg13cmos5l** and the
allocation is **8x4** at a **20 ns** target. Another IHP PDK is not interchangeable.
The official composites' transitive dependencies remain an observed trust
boundary, so audits retain the actual resolved job identities.

The configured 85-entry flow preserves the original 80 entries plus five
project integration entries. Some entries are conditionally skipped by the
frozen configuration. Required acceptance checks must produce passing results;
an entry count is not an executed-stage count. The complete original Magic
checker remains enabled with the exact documented contact-rule alignment.
The fast timing set combines -40 C standard cells and -55 C SRAM. See
[verification](verification.md) for this boundary and the functional zero-delay
scope of netlist simulation.

## Replay retained evidence

The following commands recheck original archives and recorded results into
fresh directories. They do not rerun the original solver or physical design:

```sh
python3 evidence/E0045-g2-sram-qualification/ci-94a3082/verify.py --output build/physical-replay --controls
python3 evidence/E0045-g2-sram-qualification/ci-default-75c1e7d/verify.py --output build/production-replay
```

Use the pinned Linux workbench for both. The physical replay also supports
Windows; the default-production replay requires Linux because its frozen
waveform parser emits native line endings. Each retained README states its
own requirements. [G3 evidence](../evidence/E0046-program-toolchain/README.md)
provides program-tool and publication replay instructions. [G4 evidence](../evidence/E0047-g4-submission-candidate/README.md)
records the fresh final-run audit and reproduction separately.

CI artifacts have retention limits. Curated repository archives and release
assets retain the identified bytes beyond the original job's download window.
Verify checksums, source and scope before treating any downloaded artifact as
qualification. Registry manifest/config and layer-HEAD checks establish public
identity/access; they do not claim that every image layer was downloaded.

## Historical and optional lanes

M0's original 6x4 template and physical lock remain historical. E0010 reproduced
its accepted layout apart from GDS timestamps. G1/E0031 later qualified the
8x4 compact10 experiment; G2/E0045 separately qualified and adopted SRAM.
The [source registry](sources.md), original [template inventory](upstream-template.json)
and per-experiment records preserve these different conditions.

FPGA and optional devcontainer workflows remain available but do not establish
board compatibility. No FPGA bring-up or fabricated-silicon observation is
claimed. Engineering checks and the owner's pending M0 fluency gate remain
separate.
