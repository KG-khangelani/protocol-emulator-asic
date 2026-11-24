# E0050 — Powered cold loader on the released chip interface

24 November 2026. From source `550065b9e7ac1e5eeafd081854d766ae100de5ec`,
the `ColdLoad` command verified the 32-byte v0.1.0 receiver over the modeled
shared bus, then received `0x96` and `0x69` with the released host reader at
terminal `0xA7`. The runner checks the receiver's source and binary identities.
All four starting artifacts also match the original G4 program archive. The
fixture ties the chip's enable high, counts real simulated clock edges, and
observes the separate host, chip and peer drive masks. [UART result](uart-result.json) · [Full UART observations](uart-transcript.json.gz) · [Acceptance decision](../../docs/decisions/0052-engineering-first-powered-loader.md)

## What was checked

| Observation | Result |
| --- | --- |
| Clock and bus handoff | The controller kept the peer isolated through all writes, byte reads, length and payload checks. The last two loader clocks were edges 75 and 76 at selector `E7`. At edge count 76 the observed selector settled at `67`, then `00`. The host and chip drive masks were zero throughout that handoff, and the UART peer owned UIO1. |
| G3 programs | Each backend matched the 55 original cases and all 54,522 normalized observations, including 15 expected rejections. These include bank boundaries through 128 words, UART framing and host delivery, SPI in four modes and both bit orders, and 18 I²C cases. |
| G5 waveform | Each backend matched twenty cases, including four expected rejections and 1,262 runtime observation rows. The comparison checks full loader and runtime records with only the registered powered selector/enable projection. The release's twenty-first case deliberately deselects the macro during execution. |
| Failed handoffs | A one-bit write corruption made the second program byte read as `01` instead of `00`. A stuck-connected idle-high transmitter was rejected before the reset edge. An extra runtime clock and a dropped `67` transition were each detected before the controller reported launch. After each rejection the clock was parked, host drivers released, reset asserted and selector set to `E7`. A fresh cold start then passed. |
| Chip and fixture identity | The production guard verified all twenty hardware inputs. Verilator used production RTL. Icarus used the submitted netlist extracted from the original G4 archive, its two-run identity, the qualified SRAM models and the three digest-checked PDK cell models. Both backends executed eight required test groups. [RTL receipt](rtl-qualification.json) · [Netlist receipt](netlist-qualification.json) · [Producing inputs](inputs.json.gz) |

The full 1,160-case I²C matrix belongs to E0049. This product check reused the
released runtime drivers and exercised the eighteen I²C cases in G3. A custom
SPI image also ran through the command's ordinary artifact-directory entry
point and produced `uio_oe=0C`, `uio_out=08`, `uo_out=21` on its first edge. [Custom SPI result](custom-spi-result.json) · [Custom SPI trace](custom-spi-transcript.json.gz)
The simulator proves digital pin order and behavior under the modeled
environment. Physical isolation, line release and receiver timing still need
a calibrated fixture. [Earlier I²C matrix](../E0049-review-council/powered-netlist/i2c-matrix/result.json) · [Physical test design](../E0049-review-council/panel-b/etr-fixture.md)

## Reproduction

From a checkout on H: with the locked workbench installed, run
`.\tools\workbench.ps1 ColdLoad`. The default writes a fresh run under
`build/cold-load/`. For the two full comparisons, run the following from the
repository root inside the locked Linux workbench. Use fresh output names.
The first command fetches the pinned upstream cell models and checks each
digest. The simulator commands can then run offline.

```sh
python3 -B evidence/E0049-review-council/powered-netlist/run.py fetch-models build/host-t01-pdk
python3 -B evidence/E0050-powered-cold-loader/reproduce.py --backend icarus --pdk build/host-t01-pdk --out build/host-t01-netlist
python3 -B evidence/E0050-powered-cold-loader/reproduce.py --backend verilator --out build/host-t01-rtl
make check
```

The clean replay used image ID
`sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909`,
read-only committed sources and fresh output on H:. The simulator receipts
record the command, reference hashes, test results and adverse observations.
Both runs bound the same 371 producing files. Each digest matched its Git blob
at `550065b`. Eight older files in the existing Windows checkout had CRLF
line endings, so use the committed checkout for exact input-manifest replay.
The two record indexes and all 75 decompressed case traces were byte-identical
across the clean backends. The repository check executed 163 unit tests.
[Repository check](check.log.gz) · [Icarus test report](netlist-results.xml) · [Verilator test report](rtl-results.xml)

The first integration run failed at cocotb module discovery. The next run
exposed an unknown chip direction before the first reset edge, where both
external drivers were released. The logger now records that four-state value
as observed. Both failures preceded any successful UART demonstration.
[Discovery failure](first-discovery.log.gz) · [Pre-reset observation failure](first-reset.log.gz)
