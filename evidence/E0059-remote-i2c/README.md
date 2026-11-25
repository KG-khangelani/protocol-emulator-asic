# E0059 — Board 4 returned the requested I²C data and recorded extra clock transitions

**On FabricFox board 4, both firmware images read the requested byte from the RP2350B I2C1 peripheral. Across three complete captures, 12/12 addressed reads returned the correct value and 6/6 intentionally unanswered addresses produced NACK. Zero of the 18 raw captures met the clean-edge criterion.** The sampler recorded additional SCL high and low intervals spanning one to three 100 ns samples. The finding makes receiver-side measurement of the physical clock a priority. [Prospective test](../../docs/decisions/0061-try-i2c-on-a-hardware-target.md) · [Original raw records and source identities](manifest.json)

| Cold loads on board 4 | Correct read bytes | Address NACKs | Raw clean decodes | SCL transitions in successful transfers |
| --- | ---: | ---: | ---: | ---: |
| Native target pull-ups, first complete capture | 4/4 | 2/2 | 0/6 | 132–260 |
| Added RP2350 input pull-ups on the HAT-linked SDA/SCL pins | 4/4 | 2/2 | 0/6 | 112–192 |
| Native target pull-ups, fresh repeat | 4/4 | 2/2 | 0/6 | 152–260 |

A clean combined transaction in the digital reference has 76 SCL transitions. Every unfiltered physical trace contained extra transitions. A diagnostic that waited for five consecutive equal samples of SDA or SCL decoded all 18 expected exchanges, including the ninth bit of each byte. That filter was selected after examining the first record. The native-bias start-to-STOP interval on successfully addressed transfers was 1.6788–1.6790 ms with that decoder. With the extra pull-ups it was 1.6417–1.6418 ms. The bias trial did not produce a clean unfiltered decode. The captures do not distinguish an analog threshold recrossing, an effect of board wiring, or a sampling artifact. No probe measured voltage or actual resistance. [Native capture](native-first/decoded.json) · [Bias control](bias-control.md) · [Added pull-ups](linked-pulls/decoded.json) · [Fresh native repeat](native-repeat/decoded.json)

## Fixture and evidence

Two fresh synthesize/place/route runs produced the same configuration. The router estimated 13.31 MHz on the constrained internal paths and accepted the requested 12.5 MHz. The RP2350 clock generator used a 125 MHz system clock and a ten-cycle period. Another state machine sampled the target-end GPIOs at a nominal 10 MHz into DMA. The two state machines share a timebase. The probe captured SDA, SCL, a copy of the controller's SDA pull-low enable, and HALT. Each pin-change journal reconstructs all four observed bits throughout the 24,000-sample window. The capture does not include an SCL-enable witness. [First route](route-a.json) · [Second route](route-b.json) · [FPGA wrapper](../../experiments/remote_i2c/fabricfox.v) · [Provider wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html)

The FPGA's logical SCL and SDA route to GPIO27 and GPIO26. The two bus cells can only drive zero. The native target exposed a 256-byte memory at address `2E`. Each 96- or 108-word image used the register offset written on the bus to retrieve `01` at `96` or `A5` at `55`. For the NACK control, the native target used `2F` while the FPGA requested `2E`. Every run read back the entire program and its length, address and payload presets. The terminal FPGA result showed HALT, released bus outputs and the expected marker. The NACK path committed raw zero with valid set; the marker distinguishes it from a successful payload. [Target driver interface](https://docs.micropython.org/en/latest/library/machine.I2CTarget.html) · [Retained implementation](../../experiments/remote_i2c/on_board.py) · [Independent pin decoder](../../experiments/remote_i2c/check.py)

The first attempt retained three complete release-image traces, then the RP2350 ran out of memory formatting a record. Those partial trials are excluded from the table. Emitting smaller pin-change records completed the six cases. The board manager then failed to allocate a contiguous 104,090-byte programming buffer when restoring its stock design. The capture and GPIO cleanup had finished. Reconnecting to the unoccupied board and performing a standard MicroPython soft restart restored the factory selection. The later two sessions completed capture and restored the stock gallery selection directly. All retries ran on board 4. [First error](initial/allocation-result.json) · [Complete capture with restoration error](native-first/result.json) · [Confirmed recovery](initial/soft-restore.json) · [Final board receipt](native-repeat/result.json)

## Reproduce

The offline audit needs Python 3.11+ and the repository's checked-in inputs. The strict checker exits nonzero for these measured waveforms. Its report-only option prints the complete table for inspection. In the locked workbench, add `--verify-payloads` to the audit to reassemble the exact MicroPython jobs for the two final sessions.

```powershell
python -B evidence/E0059-remote-i2c/audit.py
python -B experiments/remote_i2c/check.py evidence/E0059-remote-i2c/native-repeat/terminal.bin.gz --report-only
```

For a new board session, use a fresh H: directory and the Docker `$mounts` and `$image` setup in [the digital replay](../E0058-i2c-guard/README.md#reproduce). Fetch the pinned terminal client into that directory. The public board runner checks the visitor count and current selection before programming. Add `--linked-pulls` for the alternate bias and supply a fresh output name each time.

```powershell
docker @mounts --network none $image python3 -B experiments/remote_i2c/build.py build/route
docker @mounts $image python3 -Bc "from urllib.request import urlopen; from pathlib import Path; from hashlib import sha256; from experiments.remote_uart.run import WHEEL,WHEEL_URL,WHEEL_SHA; raw=urlopen(WHEEL_URL,timeout=30).read(); assert sha256(raw).hexdigest()==WHEEL_SHA; (Path('build')/WHEEL).write_bytes(raw)"
docker @mounts $image python3 -B experiments/remote_i2c/remote.py --board fpga-4 --image build/route/image.bin --wheel build/websockets-15.0.1-py3-none-any.whl --out build/native
docker @mounts --network none $image python3 -B experiments/remote_i2c/check.py build/native/terminal.bin.gz --report-only
```

For the receiver qualification, repeat on a known load with calibrated, simultaneous SDA and SCL measurements at the target, retaining the unfiltered waveform and the SDA/SCL drive commands. Sweep both firmware images, measure threshold-crossing order, rise time and data-valid time, and record measurement uncertainty. Keep the released program selected until that comparison can decide the guard. [Equipment sources in the Western Cape](../../docs/research/western-cape-bench.md) · [Receiver acceptance criteria](../../docs/research/council-2026-11-24/next-experiments.md#3-measure-one-claimed-external-interface)
