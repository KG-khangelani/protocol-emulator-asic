# Replay the powered host, selector handoff and resident I2C checks

The records pair tests with their frozen contracts. The host study checks fifteen published programs, the selector study enumerates 720 bit orders, and the resident study contains a rejected cold-equivalence claim and a subsequent valid-gated diagnostic. An isolated Windows starter test and a common reset edit in the council's VM and PIO examples measure software entry points. [Resident findings](resident-review.md) · [Operator comparison](owner-comparison.md)

## Inputs and tools

Use a complete Git checkout with the v0.1.0 and v0.1.1 objects and E0047/E0048 artifacts. The runners read the G4 release source at `5bdc0e6b6449a829a5da1f8f9a8060257e974843`, the G5 release at `022834146efcb5f388a4d6ec23b3b705a0df7ef8`, the archived G4 submitted netlist and the exact two SRAM model blobs. Hardware results use functional digital models. Linux Icarus reads anonymous memory files for the large gate executable. The submitted G4 archive SHA-256 is `7348d2fc9e448ada84974b450801ee7cd5aa0b3065e1569fceefd6a154ad3ee2`.

Use Python 3.11 or later and Docker with a Linux workbench containing Icarus, vvp, Git and cocotb. The council used local image ID `sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909`, Icarus 14 development build `s20260301-328-geda9fdcd1-dirty` and cocotb 2.0.1. The runner reported Python 3.11.16 and the simulator's cocotb startup logged its embedded interpreter as 3.11.9. Native Windows starter and orchestration used Python 3.14.6. The public G4 release advertises a separately pinned package `ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:a22fc6626bc4f61b52cd6a32793cec86f718f0943d078ad03cfbf8dc7932af88`. A host can obtain that release image in advance, then pass its selector to the runner. The runner records the actual local image ID. Tool differences can change four-state initialization in the original failing harness. [Published G4 image and source](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0)

The gate tests use three upstream files totaling 131,300 bytes. The fetcher requests only those files at IHP commit `89d42ee6d2fd9b50b86a1aada6fee6673c3e6008`, verifies all SHA-256 values, then writes the files under a fresh directory. Alternatively pass an existing `ihp-sg13cmos5l/libs.ref` with those exact files to `--pdk-libs`. Network access is disabled for all simulator containers. [Exact IHP URLs, sizes and digests](records/pdk-source.json)

## Run from the repository root on H:

Set `$kit` to the directory containing this README and the Python/Verilog files. Each output directory must be new. The optional matched PIO/VM edit also requires a native Node executable and panel A's small pinned pioasm and rp2040js tool set. To replay just the powered launch, selector, resident, starter and delivery checks, omit the PIO fetch and the `--pio-tools` argument.

```powershell
$repo = (Get-Location).Path
$kit = (Get-ChildItem "$repo/evidence/E0049-review-council/panel-c" -Recurse -File -Filter replay_records.py | Select-Object -First 1).DirectoryName
$output = (New-Item -ItemType Directory -Path "$repo/build/council-panel-c-replay-01").FullName
$reviewImage = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
python -I -B "$kit/fetch_pdk_models.py" --out "$output/models"
python -I -B "$repo/evidence/E0049-review-council/panel-a/pio/fetch_pio_tools.py" "$output/pio-tools"
python -I -B "$kit/replay_records.py" --repo "$repo" --out "$output/results" --pdk-libs "$output/models" --image "$reviewImage" --pio-tools "$output/pio-tools"
```

The wrapper compiles and executes the original startup harness, the corrected powered-host sequence, the exhaustive selector study, the strict resident negative, the valid-gated resident matrix and the native starter commands. With the optional PIO tools it also compiles the common edit, runs Icarus and rp2040js and compares their public outcomes against the two preserved originals. The original host and strict resident processes are expected to exit nonzero. The wrapper requires their specific failing observations and archives them in the fresh output before continuing. The final status is `PASS_PANEL_C_REPLAY`.

## Expected observations

| Test | Expected outcome |
|---|---|
| Initial startup harness | Unknown first-edge status under the original Icarus version. The record preserves the testbench and original failure. |
| Corrected startup and independent pad-only check | 15/15 powered variants match reference after run, 15/15 naive variants diverge, 9,811 sampled post-load edges per profile. The input-mutation trial fails its first program-byte readback. |
| Monotone selector orders | 12,966 equal RTL/netlist rows, SHA-256 `4029566ae59b247f481794712037f3db3505d93f09f0e50b7aa65f48001b7a4d`. Of 720 orders, 360 expose a loader read. All 120 bit-7-first tails and the deliberate E7 → 67 → 00 route preserve release. |
| Resident strict comparison | Changed transaction finishes correctly, but retained raw RX differs on 78 of 373 event rows while valid is zero. Two compact failed raw traces permit reinspection. |
| Resident valid-gated diagnostic | Five completed combined-I2C transactions each on RTL and the G4 netlist. Both return observation SHA-256 `3832c1e216d44946c5d8ebc6a75fc771cdbcf8474c466e6438251426782d6a4f`. Bank invalidation and unknown custody reject before a new run. Distinct images share the endpoint and length. |
| Starter and source edit | Two release examples reproduce all eight output files and pass the twelve checker unit tests. For the optional common edit, all ten cases per implementation shift only the requested edge interval/terminal offset as predeclared. |

The strict and corrected host runs share the production RTL and simulator. The selector and resident studies compare different representations of the hardware under one simulator. The PIO and ASIC edit checks share the prescribed operation and scoring logic. The independent tasks, tools and inference boundaries are recorded in each contract.
