# What smaller program files would buy

The [declared dictionary](contract.md) reconstructed every instruction in all fifteen released programs. The original archives were hash-checked. Each G3 binary matched G5's preserved copy, and the two G5 binaries matched their clean reproduction and native Windows copies. Six files shrank and nine grew. A file with 128 distinct legal instructions expanded to 628 bytes. All five malformed streams were rejected. [Per-image results and controls](result.json)

| Program family | Independently loaded images | Original bytes, summed | Dictionary bytes, summed |
| --- | ---: | ---: | ---: |
| I²C write, read, combined | 3 | 812 | 376 |
| SPI host | 8 | 288 | 320 |
| UART | 2 | 64 | 70 |
| G5 waveform | 2 | 160 | 156 |
| Entire collection | 15 | 1,324 | 922 |

The three I²C images account for 436 bytes saved, exceeding the 402-byte net collection saving. The other twelve together grow from 512 to 546 bytes. The maximum individual file fell from 384 to 148 bytes for the combined I²C program. Its ninety-six words use twenty-one distinct values. The all-distinct control requires a four-byte header, 512 bytes of literals and 112 bytes of seven-bit indexes. Even a raw fallback with the same explicit format header occupies 516 bytes. These are file sizes for a deterministic lossless encoding. The codec runs before loading and has no mechanism to change a runtime edge.

Panel A applied the same rule to two held-out council programs. The 85-word VM 1-Wire image encoded in 126 bytes, the 59-word target in 109. Each still requires the standard full readback when expanded and loaded onto interface 0x22, respectively 712 and 498 clocked steps. The 1-Wire PIO image comprised 32 distinct 16-bit words, so its dictionary grew to 88 bytes. With a four-byte raw fallback and four-byte FIFO preload it travels in 72 bytes. A dense VM index can straddle a 32-bit row, and an on-chip dictionary may need both an index read and a literal read for a single instruction. Branches and the peak memory configuration must be charged before claiming a fixed-cycle, smaller implementation. [Held-out evaluation](held-out/assessment.md)

For arbitrary public readback of 128 independently written 32-bit words, the persistent implementation must distinguish at least 2^4096 possible data values before considering validity or control. The installed 256×32 macro provides 8,192 physical bits in either case. Host pre-expansion can save distribution bytes but keeps the same loader and installed macro. The council found no requirement for a smaller distribution file. Mixed short/long native encodings are another design option, with different fetch, decoding and alignment costs. [RISC-V compressed instruction specification, §25.1](https://docs.riscv.org/reference/isa/v20240411/unpriv/c-st-ext.html)

From the repository root, use a new output file under `build/`. The held-out checks print their records on standard output.

```powershell
python -B evidence/E0049-review-council/storage-screen/screen.py build/council-storage-replay.json
python -I -B evidence/E0049-review-council/storage-screen/held-out/count.py
python -I -B evidence/E0049-review-council/storage-screen/held-out/compare_formats.py
```
