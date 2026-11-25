# E0063 — The three retained FPGA images run in a model of the Lattice breakout headers

**An original Raspberry Pi Pico can connect every project pin on a Lattice ICE40UP5K-B-EVN.** All 26 SG48 package pads in each archived image reach J2 or J3 in the vendor schematic. Two fresh executions reproduced UART delivery, SPI abort and timeout recovery, two I²C firmware loads, and a 17-slot 1-Wire exchange through those simulated header connections. The project clock enters on J3.8. This supplies a specific FPGA part number and wiring for the Western Cape bench without a new place-and-route run. [Decision](../../docs/decisions/0065-check-the-local-breakout-at-its-headers.md) · [Full wiring table](../../experiments/local_breakout/wiring.csv) · [Local shops](../../docs/research/western-cape-bench.md)

The evidence is a schematic check, packed-netlist simulation and Pico software cross-compilation. A physical Lattice board label, continuity measurement, actual sensor identity and calibrated branch waveforms remain outstanding. The two public FabricFox boards responded on 25 November. Their documented pin paths and the available host hardware exposed no calibrated target-branch capture or connected DS18B20. The local host listed COM1 and six Bluetooth ports. [Access record](access.json) · [Provider pin map](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Earlier laboratory search](../E0053-uart-baud-offsets/README.md#remote-instrument-access)

| Header simulation, nominal 12.5 MHz | Outcome in each run |
| --- | --- |
| Raw UART, E0051 | Verified all 32 program bytes, then delivered `96 69` (hex). An opposed peer on UIO1 produced an unknown bit. A wrong write, malformed stop and too-short loader clock each triggered their expected rejection. |
| Staged SPI, E0057 | Verified 504 bytes. Normal A4/A5 commands returned 3C/A7. An invalid command left MISO released throughout. Two aborts, one from each driven level, reached digital release at 296 and 376 ns and delivered the fresh A7 reply at a 640 ns handoff. The selected stall halted at 5.808 µs. All sampled MISO pad states agreed with the independent enable witness. |
| I²C release and guard, E0059 FPGA | Verified 384 and 432 program bytes. Both read register 96 at address 2E and received 01. Each wrong address produced a NACK. START to STOP was 1.5737 ms for the read and 419.6 µs for the NACK on both images. |
| 1-Wire, same E0059 FPGA | Verified 340 bytes. The two modeled power responses each produced a 500 µs reset, 25 µs presence delay, 96 µs presence, `CC B4` and the seventeenth read slot. The sampled bits were 1 and 0. The empty and stuck-low cases halted with `98` and zero command slots. |

All four staged firmware loads detected a deliberate one-bit error at read selector `81`. Icarus resolved the SPI pad with the external requester listening. Its four-state value could be checked directly against the exported enable. The simulated transition times omit board propagation, output buffer turnoff, load and instrument error. The two runs share the cells, stimuli and scoring code. [First result](first.json) · [Repeat](repeat.json) · [Cold comparisons and pin samples](header-logs.json.gz) · [Archived-input manifest](manifest.json)

## Assemble the proposed fixture

Use the exact SG48 breakout and the original wired RP2040 Pico or Pico H. Follow the CSV's physical Pico **header pin** column when wiring. A GPIO number and its header number often differ. The Lattice schematic marks J2 and J3 as unpopulated. Inspect the board and fit two straight 2×10, 2.54 mm connectors if needed. Open all four SW2 switches before powering. Three switch nets are used, including SG48 pin 43, an FPGA output. A closed switch grounds its net. The board guide identifies a 3.3 V I/O supply. With both boards USB-powered, connect common ground (e.g. J3.19 or J2.20 to Pico header 23) and leave their regulator outputs separate. Check orientation and continuity with power removed. [Lattice guide, pp. 12, 15–16, 27–28](https://www.latticesemi.com/view_document?document_id=51987) · [Pico pinout](https://pip-assets.raspberrypi.com/categories/610-raspberry-pi-pico/documents/RP-008309-DS-1-Pico-R3-A4-Pinout.pdf?disposition=inline)

Use Diamond Programmer's volatile **CRAM Programming / Fast Program** operation with J6 shunted 1–2 and 3–4, as illustrated in figure 8.4. Select the corresponding retained binary and check its SHA-256 against either result file. Program the FPGA before enabling the Pico's outputs. Supply the nominal 12.5 MHz bench clock from Pico GP27 (physical pin 32) to **J3.8 / SG48 pin 20**. The separate onboard 12 MHz oscillator goes to J2.16 / pin 35. It can stay on that unused net. [UART image](../E0051-fabricfox-uart/fabricfox-v2-12p5mhz.bin) · [SPI image](../E0057-remote-spi/fabricfox-spi.bin) · [Open-drain image for I²C or 1-Wire](../E0059-remote-i2c/fabricfox.bin)

| Measurement | Signal points on this breakout | Physical acceptance |
| --- | --- | --- |
| I²C | SDA J3.3/GP18, SCL J3.5/GP19 at the Pico I2C1 receiver. FPGA SCL pull-low witness J2.10/GP9, SDA witness J3.18/GP21. | Measure supply, pull-ups, total load, thresholds, actual SCL/SDA edges and skew on both programs. Score setup, data validity and rise time against the declared mode and receiver with uncertainty. [I²C criteria](../E0058-i2c-guard/README.md) |
| SPI | CS J3.5/GP19, SCK J3.17/GP17, MOSI J3.3/GP18, MISO J3.20/GP20, enable J3.18/GP21. | Use a calibrated branch-current or differential measurement under both limited bias polarities. Demonstrate high, low and released references. Compare the upper bound on turnoff against the named requester's gap. [SPI calibration and traffic](../E0057-remote-spi/README.md#next-electrical-test) |
| UART | The shared readback/RX pin is J3.3/GP18. Isolate the transmitter during readback. Trigger from the loader selector transition. | Measure driven-high, driven-low and released references at this branch. Record handoff with both bias polarities and deliver two frames. The shared-clock local rehearsal supplies no independent-oscillator measurement. [UART reference controls](../E0052-remote-uart/README.md#remaining-electrical-question) · [Earlier independent-clock experiment](../E0054-separate-oscillators/README.md) |
| 1-Wire | DQ J3.5 to the sensor and GP19. Take the GP19 sample lead at the sensor DQ connection. FPGA pull-low witness J2.10/GP9, HALT J3.16/GP22. | Use one short, 3.3 V bus with an external 4.7 kΩ pull-up. Wire one sensor's VDD to 3.3 V for the external trial, and the other sensor's VDD to ground for the parasite trial. Verify pinout for the received package. Record markings, wiring, measured rail and resistor, lead length and the ROM from each acquisition. [DS18B20 data sheet](https://www.analog.com/media/en/technical-documentation/data-sheets/ds18b20.pdf) |

## Acquire a real sensor when the fixture is connected

Load the E0059 open-drain FPGA image. Use MicroPython v1.29.0 for the original RPI_PICO on the separate Pico. Its USB REPL is available while all 26 header GPIOs serve the fixture. The following PowerShell commands generate one external-power job, run it over a named serial port and score the actual captured samples. Use a fresh output directory per acquisition. Substitute the measured Pico port for COM5. Use `parasite` for the second sensor. For both `absent` and `stuck`, remove the sensor and leave the external pull-up fitted. The latter job applies the low using the Pico's open-drain mode. [Pico firmware](https://micropython.org/download/RPI_PICO/) · [MicroPython 1-Wire driver](https://github.com/micropython/micropython-lib/blob/master/micropython/drivers/bus/onewire/onewire.py) · [Acquisition code](../../experiments/local_breakout/sensor.py)

```powershell
$trial = 'build/sensor-external-01'
python -B experiments/local_breakout/prepare.py external $trial
mpremote connect COM5 run "$trial/pico_job.py" | Out-File -Encoding utf8 "$trial/terminal.txt"
if ($LASTEXITCODE -ne 0) { throw 'Pico acquisition failed' }
python -B experiments/local_breakout/score_sensor.py "$trial/terminal.txt"
```

Before and after the FPGA exchange the Pico enumerates exactly one family-28 device with a valid ROM CRC and addresses that ROM for its power bit. During the exchange it passes control of DQ to the FPGA and samples DQ, drive and HALT simultaneously at nominal 5 MHz for 3 ms. The scorer decodes the command from DQ, checks the returned bit at 15 µs, validates drive ownership and cross-checks the terminal marker. A high read alone also occurs when a peer ignores the command. ROM identification and known power wiring give the real trial additional evidence. The query performs no temperature conversion. [Physical withheld-reply control](../E0062-onewire-peer/README.md) · [Sensor waveform scorer](../../experiments/local_breakout/score_sensor.py)

The v1.29.0 MicroPython cross-compiler accepted all four jobs. Its own PIO assembler emitted `e401 e400` for the project clock and `4010` for the sampler. The first compile exposed unsupported starred tuple syntax. The first header simulation compile also exposed a duplicate Verilog block name. Both diagnostics and the successful reruns are retained. Hardware execution of the local acquisition remains open. [Compiler receipt](micropython.json) · [Development diagnostics](development.json)

## Reproduce offline

From the H: checkout, create a fresh output directory and mount the checkout read-only into the existing project workbench. Run the last four commands for both repetitions using different output directories.

```powershell
$repo = (Resolve-Path .).Path
$scratch = (New-Item -ItemType Directory -Path (Join-Path $repo ("build/breakout-" + (Get-Date -Format yyyyMMdd-HHmmss-ffff)))).FullName
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$mounts = @('run','--rm','--network','none','--mount',"type=bind,source=$repo,target=/workspace,readonly",
    '--mount',"type=bind,source=$scratch,target=/workspace/build",'--tmpfs','/tmp:exec','-w','/workspace',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace')
docker @mounts $image python3 -B experiments/local_breakout/run.py uart build/first/uart
docker @mounts $image python3 -B experiments/local_breakout/run.py spi build/first/spi
docker @mounts $image python3 -B experiments/local_breakout/run.py drain build/first/drain
docker @mounts $image python3 -B evidence/E0063-local-breakout/audit.py
```

For the schematic check, download Lattice guide FPGA-UG-02001-1.2 into the scratch directory. The script uses PyMuPDF 1.28.2 to pair net labels with pad and connector numbers in figures A.3 and A.4 of the original PDF. On figure A.3 the reset wire connects package signal `IOT_45A_G1`, pin 37, to off-page label `IOT_345A_G1`. Figure A.4 uses that same off-page spelling at J2.15. The checker follows both literal labels. The retained guide SHA-256 and upstream MicroPython archive digest pin the two external inputs. [Schematic checker](../../experiments/local_breakout/vendor_check.py) · [Upstream MicroPython v1.29.0](https://github.com/micropython/micropython/releases/tag/v1.29.0)

```powershell
Invoke-WebRequest 'https://www.latticesemi.com/view_document?document_id=51987' -OutFile "$scratch/guide.pdf"
python -B experiments/local_breakout/vendor_check.py "$scratch/guide.pdf"
Invoke-WebRequest 'https://codeload.github.com/micropython/micropython/tar.gz/refs/tags/v1.29.0' -OutFile "$scratch/micropython.tar.gz"
docker @mounts $image sh experiments/local_breakout/check_job.sh build/micropython.tar.gz build/compiled
```
