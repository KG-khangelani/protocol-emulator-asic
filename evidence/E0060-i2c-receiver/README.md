# E0060 — The extra I²C clock transitions stayed on GPIO27 after the target moved

**GPIO18/19 is a working connection for the native I2C1 target on FabricFox board 4.** Two complete captures with the peripheral on that pair decoded all eight addressed reads and all four missing-address NACKs directly from the target's SDA and SCL inputs. On the intervening visit to GPIO26/27, all four reads still returned the requested byte, but only one of the six transfers decoded cleanly at those pins. It was a missing-address NACK. The FPGA produced the expected clock commands on every trial. [Prospective criteria](../../docs/decisions/0062-observe-i2c-clock-at-two-inputs.md) · [Role swap](role-swap.md) · [Native SDA repeat](native-pins.md) · [Measurements](measurements.json)

| Capture group | What changed | Clean raw decodes using SCL19 | Clean raw decodes using SCL27 |
| --- | --- | ---: | ---: |
| First three sessions | Native GPIO26/27 at 10 MHz, added pull-ups at 10 MHz, native bias at 8 MHz | 18/18 | 0/18 |
| Three sessions on the four-pull-up fixture | Native target moved from GPIO26/27 to GPIO18/19 and back. Both decoders still observed SDA26. | 18/18 | 0/18 |
| Final three sessions | Captured each SDA/SCL pair together. Native target moved from GPIO18/19 to GPIO26/27 and back. | 18/18 | 1/18 |

The first six sessions recorded SDA26, SCL at GPIO19 and GPIO27, both FPGA drive commands and HALT. The last three used a single PIO input snapshot including SDA18. The program packs that snapshot before acquiring the next one. Both decoders check START, repeated START, STOP, every byte, ninth-bit ownership and the terminal marker. Across all nine sessions, **36/36** addressed reads returned their requested bytes and **18/18** missing-address requests produced a NACK. The two images were the released 96-word version and the 108-word guard. Each cold load checked all 384 or 432 occupied bytes. [Capture program](../../experiments/remote_i2c/receiver/on_board.py) · [Pin decoder](../../experiments/remote_i2c/receiver/score.py)

## What the physical signals establish

The existing FPGA image presents its SCL drive command at GPIO34. Every complete read had 76 command transitions and every first-address NACK had 20. GPIO19 had those same edge counts in all 54 trials. GPIO27 had **3,482** high or low intervals shorter than 500 ns. The FPGA held SCL released across both boundary samples of every one of those intervals. GPIO19 had none. Selecting the native target on the other pins moved the peripheral function in the RP2350 registers, but the extra transitions stayed on GPIO27. The four pad control registers read `0x5A` throughout the crossover, and PIO2's input synchronizers were enabled. This eliminates extra FPGA low commands as the explanation for those samples and identifies which pin path to probe. Voltage recrossings, local input thresholds, pickup and loading remain unresolved. [Original FPGA wiring](../../experiments/remote_i2c/fabricfox.v) · [Provider pin map](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [RP2350 register definitions](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2350/hardware_regs/include/hardware/regs/pads_bank0.h)

At the routed **12.5 MHz** core clock, the released program changed its SDA drive command **0–250 ns** after the first sampled SCL low on GPIO19. The guard gave **1,875–2,100 ns** on the same measurement across the nine sessions. Equality means both events landed in one sample. At 10 MHz sampling the first reported high at GPIO19 after an SCL release took 2.0–2.1 µs under native bias and 1.2–1.3 µs with the added weak pull-ups. These intervals run from a digital command to a digital receiver level. The sampling periods were nominally 100 or 125 ns, on the same RP2350 timebase as the FPGA clock. The transfer gives no calibrated 30%–70% rise time, physical pull-up resistance, branch load or measurement of high impedance. [Physical session statistics](measurements.json) · [50 MHz digital timing comparison](../E0058-i2c-guard/README.md)

Use GPIO18/19 for repeatable digital transactions on this fixture. For the firmware decision, capture SCL and SDA at the application receiver and, if investigating board 4, at both observed connections under a characterized load. Keep the 96-word release selected until voltage measurements show which image satisfies the receiver margin. The same remote-board inventory and provider documentation expose no calibrated probe on the UART or MISO branch. [Dated board inventory](access.json) · [Electrical qualification criteria](../../docs/research/council-2026-11-24/next-experiments.md#3-measure-one-claimed-external-interface)

## Reproduce

From the repository root, the Python audit reopens all nine raw terminal streams and the nine actual board jobs, checks the original image and receipts, re-scores both inputs, and exercises three altered-record controls. The raw jobs are retained because the capture program evolved between the three groups. Each session directory contains the submitted MicroPython source, raw board response and restoration receipt. [File identities](manifest.json)

```powershell
python -B evidence/E0060-i2c-receiver/audit.py
python -B experiments/remote_i2c/receiver/score.py evidence/E0060-i2c-receiver/full19-repeat/terminal.bin.gz
```

For a fresh public-board run, use the H:-backed Docker mounts and verified WebSocket wheel in [E0059](../E0059-remote-i2c/README.md#reproduce). The runner requires the retained E0059 configuration in the gallery and an idle board 4. These commands use different output directories. They select both native pins and then the GPIO26/27 comparison, recording both pin pairs in each case.

```powershell
docker @mounts $image python3 -B experiments/remote_i2c/receiver/run.py build/full19 --wheel build/websockets-15.0.1-py3-none-any.whl --linked-pulls --both-sda --swap-target
docker @mounts $image python3 -B experiments/remote_i2c/receiver/run.py build/full27 --wheel build/websockets-15.0.1-py3-none-any.whl --linked-pulls --both-sda
```
