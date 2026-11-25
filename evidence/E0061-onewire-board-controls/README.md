# E0061 — The FPGA rejected an absent 1-Wire responder and two stuck-line conditions

**All six board controls returned the error marker and emitted zero command slots.** The 85-word bench image produced a 500 µs reset on the four trials that started with the line high. The remaining two trials started with the line grounded by the RP2350 and issued no reset. The hardware test used an open-drain line on FabricFox board 4. Positive measurements with externally powered and parasite-powered DS18B20 sensors remain open. [Prespecified experiment](../../docs/decisions/0063-measure-onewire-negative-controls.md) · [Raw board capture](board/terminal.bin.gz) · [Physical measurements](physical.json)

| Physical condition, two cold loads each | Reset observed on FPGA drive command | DQ at HALT | Measured result |
| --- | --- | --- | --- |
| Pulled-up bus, no responding device | 500 µs in both | High on both inputs | Error 573.0–573.2 µs after reset began |
| External pin sinking DQ before launch | No drive transitions | Low on both inputs | Immediate error path, no reset or command |
| External pin continued sinking DQ after reset began | 500 µs in both | Low on both inputs after the FPGA released | Error 1,000.0–1,000.2 µs after reset began |

Every cold load read back all 340 firmware bytes, the 85-word length and both empty transmit registers in 712 loader steps. The 5 MHz digital capture sampled GPIO19 and GPIO27, the FPGA drive command on GPIO34 and HALT on GPIO30. At the terminal marker the controller had released DQ. Both physical inputs rose after removal of each injected low. On one absent-device run GPIO27 briefly recrossed before settling high. The FPGA still took the expected missing-presence path. Timing precision is limited by the nominal 200 ns sample interval, uncharacterized thresholds and interchannel delays. The public board returned to its stock configuration. [Board receipt](board/result.json) · [Receiver-path measurements](../E0060-i2c-receiver/README.md)

## The program for a real sensor

The board runs the qualified VM design at its FPGA constraint of 12.5 MHz. The experiment retimes the council's 76 µs slot firmware and moves the external-power, parasite-power and error markers to VM bits 3:2, which the existing wrapper exposes. On the production RTL, an independent target decoded `CC B4` least-significant bit first and observed the seventeenth read slot on eight combinations of presence timing and supply response. Write-one and read initiation held DQ low for 2 µs, write-zero for 62 µs. The modeled absent and held-low paths passed. A flipped command bit and a 400 µs reset both reached plausible terminal markers and were rejected by the wire checker. A second fresh build reproduced the result file byte for byte. All twelve case logs matched after accounting for the build directory in the simulator’s closing message. [Board assembly](board.asm) · [340-byte board image](board.bin) · [RTL results](rtl-result.json) · [Fresh-run hashes and log archives](rtl-repeat.json) · [Original council timing study](../E0049-review-council/onewire/rise/README.md)

For the sensor measurement, connect one identified DS18B20 at a time with a measured pull-up and known supply mode. Observe its DQ at the sensor, verify the reset and presence window, decode both commands and count all 17 slots. The external supply should give a one in the read slot and parasite power a zero. Retain an unfiltered trace for each and identify the actual device, supply, cable and load. The present board controls have no power-mode observations from a physical sensor. [Analog Devices data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf) · [Western Cape hardware sources](../../docs/research/western-cape-bench.md)

The remote-lab search found a published instrumentation bench with three externally powered DS18B20s and a parasite-powered DS1822. That paper describes a different controller and device for the parasite case. The public LabsLand FPGA fixture lists a multiplexed ADALM2000 scope, but its specification gives neither the required sensor connections nor a calibrated drive-state probe on the project's UART or SPI target branches. [Instrumentation bench paper](https://www.imeko.info/publications/tc4-2004/IMEKO-TC4-2004-036.pdf) · [LabsLand kit](https://datasheets.labsland.com/equipment/LPEQ0003)

## Reproduce

The audit reassembles the board firmware, replays the raw physical measurements and checks the twelve RTL case logs from each of the two builds. In the locked workbench add `--rebuild-job` to reproduce the exact uploaded control program. [Input and file identities](manifest.json)

```powershell
python -B evidence/E0061-onewire-board-controls/audit.py
```

For a fresh RTL regression or a fresh physical control session, use the H:-backed mounts and pinned terminal wheel in [E0059](../E0059-remote-i2c/README.md#reproduce). The second command exercises an unloaded, idle board 4 with the existing routed image. Each run needs a fresh output directory.

```powershell
docker @mounts --network none $image python3 -B experiments/remote_onewire/offline.py build/power-rtl
docker @mounts $image python3 -B experiments/remote_onewire/run.py build/power-controls --wheel build/websockets-15.0.1-py3-none-any.whl
```
