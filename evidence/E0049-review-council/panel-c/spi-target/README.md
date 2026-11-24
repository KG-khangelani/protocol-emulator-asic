# Replay the SPI target experiment

The [frozen device contract](spi-target-contract.md) specifies two response bytes, an externally timed SPI mode-0 transaction and a separate 160 ns asynchronous abort requirement. The [findings](spi-target-review.md) retain positive complete frames and the first failed bus-release observation. The [follow-up diagnostic](spi-abort-diagnostic.md) compares changing the single wait deadline with a bounded two-pin polling implementation.

The testbench uses the standard Tiny Tapeout ports. The external requester drives SCK, MOSI and CS on shared pins and samples resolved MISO, while the dedicated status reports HALT. Icarus compiles the five original G4 RTL files and both locked vendor SRAM models. Eight named cases additionally compile and run the archived submitted gate netlist with the three functional upstream cell models, including the same failed abort. The G4 release assembler is extracted from Git. The counterexample uses public MISO direction and pad data in digital models.

From an H: checkout with Git history, the [parent replay guide](../README.md) describes how to obtain the three hash-checked functional PDK files and an appropriate Linux workbench image. The script accepts already downloaded files or a matching `libs.ref` directory. In the PowerShell example, use an image present on this machine and a new output directory for each run.

```powershell
$repo = (Get-Location).Path
$panel = "$repo/evidence/E0049-review-council/panel-c"
$spi = "$panel/spi-target"
$out = (New-Item -ItemType Directory -Path "$repo/build/council-spi-target-replay-01").FullName
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
python -I -B "$panel/fetch_pdk_models.py" --out "$out/models"
python -I -B "$spi/spi_target_replay.py" --repo "$repo" --pdk-libs "$out/models" --out "$out/replay" --image "$image"
```

The wrapper mounts the repo, panel utilities, target sources and PDK read-only, with network access off. It verifies every retained per-implementation scoring digest and timeout trade. The output status is `REPRODUCED_COMPLETE_FRAMES_AND_ABORT_FAILURE`. The active MISO remains driven 1,563 ns after asynchronous CS deassertion in the retained failed case. The 288 RTL and eight submitted-netlist test rows, representative event logs, 405-case timeout sweep and rejected 215-word source are under `records/`. The ordinary command/reply and the failed shared-bus handover have independent acceptance conditions.
