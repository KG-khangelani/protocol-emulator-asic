# FabricFox v2 UART rehearsal

This experiment produces an iCE40UP5K-SG48 configuration of the released
protocol emulator. The chip's program store binds to four iCE40 embedded RAM
blocks for this build. The released UART program still arrives over the eight
shared pins after reset. It is absent from the configuration at startup.

From the repository root on H: with the locked Docker workbench installed,
run these PowerShell commands. Each invocation gets a fresh output directory.

```powershell
$repo = (Get-Location).Path
$output = New-Item -ItemType Directory -Force (Join-Path $repo 'build/fpga-uart-replays')
$run = 'build/' + [Guid]::NewGuid().ToString('N')
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
docker run --rm --network none --mount "type=bind,source=$repo,target=/workspace,readonly" --mount "type=bind,source=$($output.FullName),target=/workspace/build" --tmpfs /tmp -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $image python3 -B experiments/fpga_uart/run.py --out $run
```

Inside the locked Linux workbench with a writable `build/`, the equivalent
entry point is `python3 -B experiments/fpga_uart/run.py --out build/uart-fpga-01`.
The runner rejects an existing output name. Its top-level `result.json` records
source hashes, tool identities, each route, memory comparisons, observed
package pins and the SHA-256 of the packed image. Look under
`route-<selected MHz>/fabricfox.bin` for the configuration. It accepts a
clock from pin 20. A physical controller must supply the selected frequency,
park the clock for handoff and electrically isolate the UART peer during
readback. The routing constraint does not generate a clock on the board.

## Implementation and checks

- Keep the qualified five production Verilog sources. The experiment provides
  the byte-mask, synchronous read, write-through and hold behavior used by
  the production store. BIST is tied off in production. The comparison checks
  the qualified vendor model and a word-array oracle at all 256 physical
  addresses with all 16 byte masks. The existing public program-store test
  separately checks the 128-word logical interface.
- Use the upstream package wrapper with enable tied high and the original
  FabricFox v2 constraints. Route all 26 used package pins and the single
  project clock at seed 10. Try 50 MHz first and, on a frequency-only failure,
  try 12.5 MHz. Pad arrival and board delays require separate measurement.
- Pack the selected route, unpack it, require byte-identical repacking and
  decode its logic and pin routing with IceStorm. Drive the resolved pads
  with the archived E0050 cold-load sequence and the released UART host reader.
  Read back all 32 program bytes, check the clockless selector handoff and
  verify two consecutive frames. Reject a corrupt write, a digitally opposed
  readback driver, a bad stop, faulty RAM forwarding and an overclocked loader.

The wrapper and PCF are unmodified files from Tiny Tapeout LTD's Apache-2.0
support-tools commit `d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`. Only the
generated wrapper receives the project module name. The decoder receives the
same 26 package assignments in IceStorm's simpler PCF syntax. The manual
GitHub FPGA workflow identifies the upstream target. The experiment builds
locally with its own RAM binding and strict timing checks. [Repository workflow](../../.github/workflows/fpga.yaml) · [Target selection](https://github.com/TinyTapeout/tt-support-tools/blob/d66cf179e7bc4d296362ab7e2e3b344dc3c4f665/tt_fpga.py#L240-L283) · [Original wrapper](https://github.com/TinyTapeout/tt-support-tools/blob/d66cf179e7bc4d296362ab7e2e3b344dc3c4f665/fpga/tt_fpga_top.v) · [Original constraints](https://github.com/TinyTapeout/tt-support-tools/blob/d66cf179e7bc4d296362ab7e2e3b344dc3c4f665/fpga/tt_fpga_fabricfoxv2.pcf) · [IceStorm decoder](https://github.com/YosysHQ/icestorm/blob/main/icebox/icebox_vlog.py) · [Breakout guide](https://tinytapeout.com/guides/fpga-breakout/)
