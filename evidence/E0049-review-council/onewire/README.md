# DS18B20 power query on the production RTL

The single image in [power_query.asm](power_query.asm) uses 85 of 128 words, or 340 bytes. All eight combinations of presence timing and power response returned the declared result in Icarus. Each successful transaction took 109,503 execution clocks, about 2.190 ms at the assumed frequency, after 712 public load/verification steps. The independent checker decoded the two wire bytes as `CC B4` hex from samples of the resolved bus.

The absent-target case halted with error on edge 28,504. The stuck-low case halted with error on edge 50,003. Both sent zero command bits. The first-bit mutation changed the decoded command and the 400 µs reset mutation violated the width check. Both mutants reached a plausible HALT. Checking terminal state alone would have accepted them. The [result](result.json) retains each drive/release edge, decoded bytes and case disposition.

The [contract](contract.md) preceded execution in commit `2a0caf1`. The local workbench compiled the testbench at 14:44:00 UTC and finished the series at 14:44:12 UTC. It used Icarus, the five production Verilog files and both hash-checked vendor SRAM models. The wire fixture and [checker](screen.py) use the [manufacturer's command and timing description](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf). Both were written by the chair, so their interpretation of that document is a common source of error. The run used ideal pull-ups and the original chip-port load plan. A full sensor, analog thresholds, board launch, thermometry and other 1-Wire commands remain untested.

From the repository root on H:, run in the existing workbench. Pick a fresh output directory for each run.

```powershell
$mountSpec = 'type=bind,source=' + (Get-Location).Path + ',target=/workspace'
docker run --rm --pull=never --mount $mountSpec -w /workspace -e PYTHONDONTWRITEBYTECODE=1 protocol-emulator-asic-workbench:2026-07-29 python3 -B evidence/E0049-review-council/onewire/screen.py build/council-onewire-replay
```

The [fixture](power_query_tb.sv) reads every image byte back through the public bus before connecting the digital target. It samples the 16 write slots 30 µs from their falling edges and transmits a parasite-power zero only after receiving both commands in order. A three-state result and sampled pins make the experiment inspectable without access to the engine PC.
