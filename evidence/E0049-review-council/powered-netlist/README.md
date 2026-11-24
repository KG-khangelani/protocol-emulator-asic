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
