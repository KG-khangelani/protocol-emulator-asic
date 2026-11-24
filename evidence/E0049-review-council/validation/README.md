# Production checks during the council

The project provides normal `make doctor`, `make check` and `make test` targets. The last target runs the full production Icarus regression, an RTL harness smoke test and a separate check that ties the two sets of results to their inputs. The public G4 submitted-netlist work uses a different entry point. [Production verification layers](../../../docs/verification.md) · [Submitted-netlist experiments](../powered-netlist/README.md)

## First run and the waveform failure

The 16:37 UTC Icarus run passed all thirty groups, including the existing SPI, I²C, bank-boundary and abort controls. In the subsequent smoke test Icarus' FST writer reported two failed `mmap` calls and the simulator terminated before generating JUnit. `/tmp` was then a Windows H: bind mount inside the Linux container. For the retry the chair supplied a native Linux memory-backed `/tmp`, disabled core dumps and kept the public RTL, test sources, test directory and durable outputs on the same H: paths. The smoke test passed and the unmodified production provenance checker accepted both stages. The first full `make test` invocation exited unsuccessfully. [Original failure output](first-fst-failure.log.gz) · [Failed stage receipt](first-fst-failure-receipt.json.gz) · [Recovered stage pair and source identities](first-recovered-provenance.json.gz)

The bounded rerun below starts in an unused H: directory. It mounts the checkout read-only, gives `build` an isolated H: directory and copies the 45 Git-tracked test files byte for byte before mounting that copy at `/workspace/test`. This protects any existing harness waveform in the checkout when the stock target unlinks and rewrites its output. Named evidence, compilation output and waveforms live under H:. The FST writer's temporary memory disappears when the container exits. The host used Docker Desktop, with its WSL data directory on H:, and the existing pinned local workbench image. [Exact environment and entry point](replay.ps1)

**The clean command passed end to end.** The first tool stage started at 16:53:17 UTC and the final provenance file was written at 17:10:10 UTC. Doctor matched the pinned tools. `make check` passed the repository and learning-record checks and 159 unit tests in fifteen discovery groups. `make test` passed all thirty RTL groups and the one distinct RTL harness smoke group. The four public case files contain 1,052 SPI, 1,160 I²C, four boundary and 36 abort records. A separate current-bank check passed all 44 observations. They matched their original reference bytes in both invocations. The stage receipts record different documentation commit heads as council work progressed. The complete verification input dictionaries agree across the two invocations. [Machine-readable summary](normal-checks.json) · [Production provenance](normal-provenance.json.gz) · [Doctor output](normal-doctor.log.gz) · [Repository checks](normal-check.log.gz) · [Thirty-group JUnit](rtl-junit.xml.gz) · [Harness JUnit](rtl-harness-smoke-junit.xml.gz)

```powershell
.\evidence\E0049-review-council\validation\replay.ps1 -RunName fresh01
python -B evidence/E0049-review-council/audit.py
python -I -B evidence/E0049-review-council/validation/audit_controls.py
python -B tools/production_sram.py
```

The three audit controls keep the original evidence files untouched. Going from seventeen remote slot starts to sixteen while leaving the terminal marker intact failed the 1-Wire check. Restoring the nominal UART service limit to a +2% transmitter failed the service-bound check. Moving one public MISO release to 160 ns while retaining the late stopped-high observation in the other case failed the PIO check. Each produced the intended rejection. [Control definitions](audit_controls.py)

## Replay from committed files alone

At 17:06 UTC the chair exported forty files directly from commit `928ad99` to a fresh H: directory. The archive included panel C's target programs and raw cases, panel A's independent case reduction, and panel B's current-fixture and remote-receiver calculations and reference JSON. Isolated Python processes, with their working directory inside the extracted archive, reproduced the two electrical JSON objects and the target counts, abort edge times and disjoint wait-operand ranges. This checks that those reductions run from shareable repository content. The standard-library programs used the recorded observations and analytical models. [Result hashes and source revision](committed-only-replay.json)

A full `git archive` of the E0049 directory also supplies these inputs. Run the commands below from the extracted repository root.

```powershell
python -I -B evidence/E0049-review-council/panel-a/spi-target-crosscheck.py
python -I -B evidence/E0049-review-council/panel-b/fixture/fixture_sensitivity.py
python -I -B evidence/E0049-review-council/panel-b/sources/onewire_load.py
```

## Closing second-simulator check

At 17:12 UTC the chair reserved up to thirteen minutes for the normal `make test-verilator` target before closing. Use the same pinned image and production source as the successful Icarus command. Accept only all thirty required JUnit groups, the four source-bound SPI/I²C/boundary/abort files with their original digests, and the current-bank control. Compare the actual case bytes between simulators. A compile error, a missed deadline or an absent receipt is an incomplete check. This tests a second simulator on the full current suite. The input expectations and vendor functional models are shared.

The Verilator stage started at 17:12:38 UTC and produced its passing receipt at 17:19:58 UTC. All thirty groups passed. All four case files and the separate bank-control file were byte-identical to the fresh Icarus results. The two stage receipts contain identical verification-input dictionaries. [Cross-simulator byte counts and hashes](cross-simulator.json) · [Native Verilator receipt](rtl-verilator-receipt.json.gz) · [Verilator JUnit](rtl-verilator-junit.xml.gz)

At report revision `91a9b99`, the chair also repeated `make check` in an unused output directory. It completed at 17:23:16 UTC with all 159 unit tests and the repository metadata and learning checks passing. [Closing repository-check log](closing-repository-check.log.gz)

To repeat the second run after `replay.ps1 -RunName fresh01`, choose an unused H: output directory. The stock target materializes its build in that directory. The read-only test-source copy already exists from the first command.

```powershell
$repo = (Get-Location).Path
$out = (New-Item -ItemType Directory -Path 'build/council-verilator-replay-01').FullName
$tests = (Resolve-Path 'build/council-2026-11-24/chair/validation/fresh01/test').Path
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$mounts = @('--mount', "type=bind,source=$repo,target=/workspace,readonly",
    '--mount', "type=bind,source=$out,target=/workspace/build",
    '--mount', "type=bind,source=$tests,target=/workspace/test,readonly")
$envArgs = @('-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace','-e','PYTHONDONTWRITEBYTECODE=1')
docker run --rm --pull=never --init --network none --read-only --ulimit core=0:0 --tmpfs /tmp:rw,mode=1777,size=64m @mounts @envArgs -w /workspace --entrypoint timeout $image --kill-after=10s 780s make CURRENT_ARTIFACTS=/workspace/build/current test-verilator
```
