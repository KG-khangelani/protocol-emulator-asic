# Selected-project launch on the submitted G4 gate netlist

Under the [registered conditions](contract.md), 55 of 55 G3 case records matched the originals, including all 15 expected rejections. The four executed groups contributed 54,522 normalized observations. The comparison included UART traffic and bounded two-byte delivery, SPI in all modes and bit orders, I²C including peer responses, and loader boundaries through 128 words. The source image bytes and the protocol oracles came from G3. Every rising edge in this run had project enable tied high.

The first attempt stopped at test discovery before any simulated transaction. The [diagnosis and original log](first-attempt/README.md) retain the cause. The successful run started at 14:55:30 UTC and completed at 14:56:23 UTC using the local workbench. [Result](result.json) · [JUnit](results.xml) · [simulator log](run.log.gz) · [case records](records.jsonl.gz)

This experiment changes the two loader-exit clocks to `E7`, followed by `67` then `00` with the clock parked. A testbench monitor rejects a low host enable request at any rising edge. The Icarus netlist has zero annotated delay. Shared-pin input levels in the G3 fixture are prescribed digital stimuli. Board-level drive ownership, electrical settling and the timing of a real peer still need their own checks.

From the root of a checkout on H:, fetch the three pinned functional PDK Verilog files, about 131 kB combined. The driver validates them against the original E0043 model hashes. The second command extracts the 3.92 MB submitted netlist from the retained ZIP, uses the released 13-image byte checks, and compares the actual records to E0047. Use fresh output names.

```powershell
python -B evidence/E0049-review-council/powered-netlist/run.py fetch-models build/council-replay-pdk
$mountSpec = 'type=bind,source=' + (Get-Location).Path + ',target=/workspace'
docker run --rm --pull=never --mount $mountSpec -w /workspace -e PYTHONDONTWRITEBYTECODE=1 protocol-emulator-asic-workbench:2026-07-29 python3 -B evidence/E0049-review-council/powered-netlist/run.py run build/council-replay-g3 --pdk build/council-replay-pdk
```

## All 1,160 original I²C cases

From 15:07:09 to 15:41:44 UTC the submitted netlist ran the full powered digital matrix. The new 580,739-byte case file matched the archive byte for byte. It contains 1,000 OK, six NACK and 154 TIMEOUT terminal dispositions. Six intentionally incorrect-program cases were rejected by the independent contract. A valid timeout or NACK disposition is part of the specified behavior. The gate test includes the real SRAM function and stays at zero annotated delay. [Preregistered comparison](i2c-matrix-contract.md) · [Result](i2c-matrix/result.json) · [All cases](i2c-matrix/cases.jsonl.gz) · [Full repeated-START witness](i2c-matrix/write_read-96.json.gz) · [Execution log](i2c-matrix/run.log.gz)

## G4 hardware and G5 software together

Verilator on the original production RTL matched all 55 G3 records, including 15 expected rejections. Both that run and a separate Icarus run on the **submitted G4 gate netlist** reproduced all twenty powered-applicable G5 cases, including four expected rejections. On each representation, 1,262 complete runtime rows equaled the original G5 oracle traces and 3,472 loader rows differed only in the prospectively specified input selector and enable fields. Byte reads and the corrupted actual byte were checked. The G5 case `paused-wall-clock` explicitly asks for two low-enable rising edges; its original chip-port evidence remains the applicable result. Verilator ran at 15:36:31–15:37:01 UTC. The gate run followed at 15:42:46–15:42:52 UTC. [Contract](cross-release-contract.md) · [Verilator result](cross-release/verilator-rtl/result.json) · [Gate-netlist result](cross-release/icarus-netlist/result.json)

After the two preparation commands above, run the following from the same repository root inside the workbench. Each output path must be fresh. Large compiled executables are disposable once the result and observation files have been checked.

```sh
python3 -B evidence/E0049-review-council/powered-netlist/i2c_matrix.py build/council-replay-1160 --g3 build/council-replay-g3 --pdk build/council-replay-pdk
python3 -B evidence/E0049-review-council/powered-netlist/cross_release.py verilator build/council-replay-cross-rtl --g3-netlist build/council-replay-g3
python3 -B evidence/E0049-review-council/powered-netlist/cross_release.py icarus build/council-replay-cross-gl --g3-netlist build/council-replay-g3 --pdk build/council-replay-pdk
```
