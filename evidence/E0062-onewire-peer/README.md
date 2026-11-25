# E0062 — A physical 1-Wire peer decoded both commands and returned both reply values

**On FabricFox board 4 the FPGA sent `CC B4` and generated the seventeenth read slot in all 12 trials.** An open-drain RP2350 state machine accepted the two command bytes in eight trials. The FPGA read four ones and four zeros as requested. In four controls the peer saw the same commands but expected `CD B4` and withheld its zero. The FPGA read a one from the pull-up in all four. A high read bit alone therefore cannot identify an externally powered device. [Prospective criteria](../../docs/decisions/0064-observe-both-onewire-replies-on-the-fpga.md) · [Measurements](measurements.json) · [Raw first capture](first/terminal.bin.gz) · [Raw repeat](repeat/terminal.bin.gz)

| Conditions over two separate sessions | Trials | Peer command check | Read at 15 µs on both DQ inputs | FPGA marker |
| --- | ---: | --- | --- | --- |
| Accepted command, reply one | 4 | `CC B4` accepted | 1 | `0x88` |
| Accepted command, reply zero | 4 | `CC B4` accepted | 0 | `0x90` |
| Peer expects `CD B4` and is configured to return zero on a match | 4 | `CC B4` received and rejected | 1 | `0x88` |

The program was the exact 340-byte E0061 board image with 712 cold-load steps before each trial. The FPGA commanded a 500 µs reset. At the peer's GPIO19 input the sampled reset low lasted 501.2–501.4 µs. Presence began 26.0–26.8 µs or 56.0–57.0 µs after the first observed high, depending on the peer delay setting. Presence lasted 97.2–97.4 µs. Controller slot starts were 76 µs apart. Its low commands lasted 2 µs for a write one or read initiation and 62 µs for a write zero. The firmware signalled HALT 70.0–70.2 µs after the read started. Both physical inputs were high at HALT. [First session receipt](first/result.json) · [Repeat session receipt](repeat/result.json) · [Firmware and physical error controls](../E0061-onewire-board-controls/README.md)

The peer timed itself from observed wire transitions. It sampled sixteen bits in hardware, compared the result to a preloaded two-byte value, and recorded the received word and acceptance decision in its FIFO. A separate PIO/DMA capture sampled at 5 MHz. The offline decoder located slot starts from unfiltered GPIO19 alone, then read both GPIO19 and GPIO27 at 24 µs in the write slots and 15 µs in the read slot. GPIO19 showed 38 transitions in every capture. GPIO27 showed 38–112, although both receivers agreed at every specified sample. The FPGA command, peer and recorder shared the RP2350 oscillator. These are digital pin timing observations with a nominal 200 ns grid. The setup contained a programmable responder. It supplies no measurement of an actual sensor's power mode, its charging current, or the voltage at a sensor. [Hardware peer and capture](../../experiments/remote_onewire/peer/on_board.py) · [Independent wire decoder](../../experiments/remote_onewire/peer/score.py) · [Receiver comparison](../E0060-i2c-receiver/README.md)

The remaining device trial uses one identified DS18B20 at a time. As a separate preflight, read its 64-bit ROM with command `33`, check family `28` (hex) and verify the CRC byte. Then record its known VDD connection, sensor-side DQ, presence pulse, command bytes and seventeenth slot with the same pull-up and wiring in the two supply configurations. In particular, inspect the command bits when the reply is high. [DS18B20 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf) · [Western Cape bench sources](../../docs/research/western-cape-bench.md)

## Reproduce

The offline audit checks both raw captures, the submitted board job, all cold-load readbacks and both restoration receipts. It changes a peer acceptance record, a terminal marker and one input's read sample in memory to verify rejection. In the pinned Docker workbench `--rebuild-job` reassembles the upload. [File and input identities](manifest.json)

```powershell
python -B evidence/E0062-onewire-peer/audit.py
```

For another session, use the H:-backed mounts and terminal wheel in [E0059](../E0059-remote-i2c/README.md#reproduce), an idle board 4 with the retained image, and a new output directory. A separate offline scoring command reads the raw capture.

```powershell
docker @mounts $image python3 -B experiments/remote_onewire/peer/run.py build/onewire-peer --wheel build/websockets-15.0.1-py3-none-any.whl
docker @mounts --network none $image python3 -B experiments/remote_onewire/peer/score.py build/onewire-peer/terminal.bin.gz
```
