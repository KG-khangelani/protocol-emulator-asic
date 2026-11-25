# E0066 — Identify and power-check the two sensors with a Pico alone

The original Raspberry Pi Pico now has a standalone sensor test. It reads a family-28 ROM and an addressed scratchpad with valid CRC, issues a 17-slot broadcast power query, and checks the addressed response again. A second Pico input records the DQ waveform. On FabricFox board 4, this acquisition identified both programmed ROMs in both response modes. It also retained a valid zero-bit capture when the responder changed its answer after the query. The 18 physical fixture trials used an RP2350B and a programmable open-drain responder. The two real DS18B20s and their supply wiring still need to be measured. [Decision and controls](../../docs/decisions/0068-check-real-sensors-before-connecting-the-fpga.md) · [Per-trial measurements](measurements.json)

## Run the purchased sensors

Use a stock Pico or Pico H with the original RP2040 and MicroPython v1.29.0. Connect **one sensor at a time**. Use 3.3 V from Pico header 36 and ground from header 23. Use a 4.7 kΩ pull-up from DQ to 3.3 V, GP19/header 25 as the open-drain master, and GP18/header 24 as a high-impedance tap on DQ. Tie the externally powered sensor's VDD to 3.3 V and the parasite-powered sensor's VDD to ground. Power down before changing the wiring. Use the package pinout supplied for the specific part. The native master uses search ROM, match ROM, read scratchpad and read power supply. It performs no EEPROM write or temperature conversion. [Pico pinout](https://pip-assets.raspberrypi.com/categories/610-raspberry-pi-pico/documents/RP-008309-DS-1-Pico-R3-A4-Pinout.pdf?disposition=inline) · [Sensor data sheet, power supply and commands](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf)

For a bare TO-92 device, connect the GP18 tap directly at the sensor's DQ lead. The 2 m sealed Strand probes expose only the cable connector. A tap there can verify communication, identity and the power classification. Report its waveform at that connector. Use the bare Stellenbosch parts to measure at an accessible device lead. For every run retain the labelled device, VDD connection, measured supply and pull-up, lead length and tap position. The GPIO capture cannot infer any of those from the bits. [Local shops and part numbers](../../docs/research/western-cape-bench.md)

Run these commands from the repository root. Use the Pico's actual port from `mpremote connect list`. The first run uses sensor A with VDD at 3.3 V. For the second, wire sensor B with VDD grounded.

```powershell
$port = 'COM5'  # replace with the connected Pico's port
$dir = (New-Item -ItemType Directory -Path ("build/sensor-pair-" + (Get-Date -Format yyyyMMdd-HHmmss-ffff))).FullName
$probe = 'experiments/local_breakout/sensor_reference/pico.py'
$score = 'experiments/local_breakout/sensor_reference/score.py'
mpremote connect $port run $probe 2>&1 | Out-File -Encoding utf8 "$dir/a-external.txt"
if ($LASTEXITCODE -ne 0) { throw 'External acquisition failed. Retain the transcript.' }
# With power removed, replace A with B and connect B's VDD to ground. Reconnect USB.
mpremote connect $port run $probe 2>&1 | Out-File -Encoding utf8 "$dir/b-parasite.txt"
if ($LASTEXITCODE -ne 0) { throw 'Parasite acquisition failed. Retain the transcript.' }
python -B $score "$dir/a-external.txt" "$dir/b-parasite.txt"
```

The pair passes when the two ROMs differ, both addressed scratchpads have valid CRCs and nonconstant data, the observed command is `CC B4`, and the two wires return one and zero under the declared power connections. Each device is identified before and after the broadcast. A high bit can also come from a device that releases DQ throughout the read. For a stronger check, repeat with B externally powered and A parasite-powered, then run the comparison below. It requires both surviving ROMs to change their reported power mode. [Pico acquisition](../../experiments/local_breakout/sensor_reference/pico.py) · [Wire decoder](../../experiments/local_breakout/sensor_reference/score.py) · [MicroPython serial runner](https://docs.micropython.org/en/latest/reference/mpremote.html)

```powershell
python -B $score "$dir/a-external.txt" "$dir/b-parasite.txt" --swapped "$dir/b-external.txt" "$dir/a-parasite.txt"
```

Once the FPGA is wired, use the two original power connections and run the E0063 acquisition for each. The following command scores both FPGA cold loads and their 17-slot waveforms and matches the ROMs, bytes and power bits to the standalone records. On the separate FPGA fixture use its published pin map, with GP19 sampling the device lead. The GP18 tap above belongs to the standalone circuit. [E0063 FPGA wiring and acquisition](../E0063-local-breakout/README.md#acquire-a-real-sensor-when-the-fixture-is-connected)

```powershell
python -B $score "$dir/a-external.txt" "$dir/b-parasite.txt" --fpga "$dir/fpga-external.txt" "$dir/fpga-parasite.txt"
```

## What the remote hardware demonstrated

The resident RP2350B ran the native MicroPython 1-Wire master on GPIO27. A separate PIO state machine listened and pulled low on the linked GPIO19. It never drove high. The retained E0059 FPGA image stayed in reset with run disabled. A different state machine and DMA captured GPIO19 unfiltered at nominal 2 MS/s for 8.192 ms around each broadcast. The peer also sampled each master or peer slot while executing a predetermined response sequence. The offline audit compares those bits with the expected ROM search decisions, addresses, commands and replies. The RP2350B, its internal pull-ups and its shared clock differ from the original RP2040 with an external 4.7 kΩ pull-up. [Board wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Scripted open-drain peer](../../experiments/local_breakout/sensor_reference/scripted_peer.py)

| Observed result | Physical trials |
| --- | ---: |
| Completed identity, scratchpad and power checks, including both ROMs with the returned power bits swapped | 11 |
| No active responder. The master found zero ROMs | 3 |
| One scratchpad checksum bit flipped. The master rejected the returned bytes | 2 |
| Nine zero scratchpad bytes. Their CRC is valid, and the master rejected the constant readback | 1 |
| The addressed power bit changed from zero to one after the captured zero. The test rejected the trial and preserved the waveform | 1 |

Across the 11 completed trials, the native master and raw decoder agreed on all 17 slots. Reset low measured 481–483 µs, presence began 24.5–25 µs later and lasted 97–97.5 µs. Write-one lows measured 6.5–7 µs and write-zero lows 60.5–61.5 µs on a 0.5 µs sample grid. All **11,652** separately sampled peer slot values matched the expected traffic through each completion or rejection. One deliberately silent power response yielded a one despite valid ROM and scratchpad transactions. It passed the single read and failed when supplied as a parasite-powered member of a pair. No calibrated voltage, physical VDD state, sensor authenticity or ASIC pad timing follows from these fixtures. [First session](first/terminal.bin.gz) · [Fault waveforms](faults/terminal.bin.gz) · [Crossover and silent response](crossover/terminal.bin.gz)

| Session | Actual UTC, 25 November 2026 | Board record |
| --- | --- | --- |
| Initial controls | 22:20:53–22:21:22 | [Receipt](first/result.json) · [Executed job](first/job.py.gz) |
| Corrupt and late-changing responses | 22:23:18–22:23:48 | [Receipt](faults/result.json) · [Executed job](faults/job.py.gz) |
| Both programmed ROMs in both modes | 22:24:15–22:24:45 | [Receipt](crossover/result.json) · [Executed job](crossover/job.py.gz) |

The corresponding local date was 26 November SAST. Each session began with zero clients and restored the factory project. Two stock-Pico compiler runs produced identical bytecode. The upstream assembler emitted `4001` for the one-pin PIO sample. `make doctor` and the final `make check` passed, including 163 unit tests. An earlier check ran its tests while the reporting command was edited and failed the input-integrity guard. The original transcript and the successful rerun are retained. The software-only comparison with the FPGA reporting command uses E0063 modeled header waveforms and labelled temporary inputs. It does not create a real sensor record. [Verification and access records](checks.json) · [Artifact and source hashes](manifest.json)

The local USB inventory contained COM1 and Bluetooth serial ports. The two live FabricFox endpoints exposed the FPGA control interface. No calibrated target-branch scope or connected physical sensor was identified. SiGPT lists custom equipment setups by arrangement. An earlier university remote lab used three externally powered DS18B20s and a parasite-powered **DS1822**. Neither source established a runnable station with the required devices and connections. [SiGPT lab and access modes](https://sigpt.ai/remote-lab/) · [University circuit and devices](https://www.imeko.info/publications/tc4-2004/IMEKO-TC4-2004-036.pdf)

## Reproduce the recorded checks

Run from the Git checkout using Python 3.11 or later. The audit verifies the 20 qualified hardware inputs, rebuilds the three jobs, decodes raw DQ, checks the deliberately changed return, exercises the reporting commands and rejects altered captures and mixed device IDs.

```powershell
python -B evidence/E0066-pico-sensor-reference/audit.py
```

For stock-Pico compilation and fresh remote trials, use the Docker Desktop mount setup from E0065 with a fresh H: scratch directory. Place the official MicroPython v1.29.0 source tarball and the pinned WebSocket wheel there. The compile script checks the tarball hash and the physical runner checks the wheel and existing bitstream. Each acquisition requires its own unused output directory and an idle board. [Container mount and wheel commands](../E0065-spi-branch-bias/README.md#reproduce) · [MicroPython v1.29.0 source tarball](https://github.com/micropython/micropython/archive/refs/tags/v1.29.0.tar.gz)

```powershell
docker @mounts --network none $image sh experiments/local_breakout/sensor_reference/compile.sh build/micropython-1.29.0.tar.gz build/cross
$wheel = 'build/websockets-15.0.1-py3-none-any.whl'
foreach ($suite in 'forward','faults','crossover') {
    docker @mounts $image python3 -B experiments/local_breakout/sensor_reference/remote.py $suite "build/$suite" --wheel $wheel
    if ($LASTEXITCODE -ne 0) { break }
}
```
