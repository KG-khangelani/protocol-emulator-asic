# E0064 — A native I²C receiver stretches the first read-data clock

Both the released 96-word program and the 108-word guard read byte `01` from a physical RP2350B receiver after it held SCL low for up to **3.94816 ms**. When the receiver replied too late or withheld its reply, the FPGA halted **4.00016 ms** after releasing SCL in all eight trials. The sampled interval including quantization is **4.00000–4.00032 ms** on this nominal 12.5 MHz bench. Keep the released image selected. The guard gave the same outcomes and still needs receiver-voltage measurements on a known load to justify its extra twelve words. [Prospective decision](../../docs/decisions/0066-measure-native-i2c-clock-stretch.md) · [I²C contract](../../docs/specs/p-i2c-controller-100k.md)

## What happened at the receiver

The FPGA wrote register `96` to 7-bit address `2E`, issued a repeated START, and requested one byte. The native I2C1 target on GPIO18/19 acknowledged and left its transmit FIFO empty. A hard interrupt recorded the read request. Foreground code supplied byte `01` after the selected delay, or withheld it through the capture. The target received the register in every trial. A pin capture sampled both native inputs, both FPGA drive commands and HALT simultaneously. The long hold appeared at SCL release 29, after the read-address ACK and before the first data bit. Both FPGA commands were released throughout the measured hold. [Board program](../../experiments/remote_i2c/stretch/on_board.py) · [Public board wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html)

| Requested delay after read request | Trials in complete sessions | Observed software service | FPGA release to receiver sampling SCL high, or to HALT | Result at the native pins |
| --- | ---: | ---: | --- | --- |
| Immediate service | 8 | 60–78 µs | Longest release to high, 89.92–105.28 µs | Eight complete reads, final NACK and STOP |
| 1.00 ms | 4 | 1.033–1.054 ms | Release 29 to high, 1.05728–1.08128 ms | Four complete reads |
| 3.85 ms | 4 | 3.895–3.915 ms | Release 29 to high, 3.92480–3.94816 ms | Four complete reads |
| 4.15 ms | 4 | 4.179–4.216 ms | Release 29 to HALT, 4.00016 ms | SCL rose 206.56–241.92 µs after HALT. The receiver held SDA low at capture end. |
| Byte withheld | 4 | FIFO stayed empty | Release 29 to HALT, 4.00016 ms | SCL remained low to capture end. SDA was high. |

The two software timestamps and the two pin events have different origins. Even an immediate reply takes time to dispatch and fill the FIFO. The protocol decoder used unfiltered samples to verify the two addresses, register, reply, ninth-bit ownership, boundaries and HALT on the 16 successes. Every timeout showed the preceding write and read-address ACK, with SCL held low through HALT. Success returned status `88`, RX `01`, valid `01`. Timeout returned status `98`, RX `00`, valid `01`. Accept a byte only after a completed transaction with the OK marker. [All release-to-high intervals, raw pages and results](measurements.json) · [Decoder](../../experiments/remote_i2c/stretch/score.py)

In the 3.85 ms trials the release image's two observed waits were 3.92480 and 3.94816 ms. The guard's were 3.92544 and 3.92736 ms. Foreground service latency varied between runs, which limits comparisons of those small differences.

PIO2 snapshotted GPIO18/19/29/30/34 once per five 31.25 MHz instructions. DMA stored 45,000 samples on a 160 ns grid for 7.2 ms. The FPGA clock came from a second PIO block dividing the same nominal 125 MHz reference by ten. For two sampled events the interval can differ from their index distance by up to one sample period. The 50,000-clock deadline plus 16 cleanup clocks allows HALT in 4.00000–4.00128 ms on this clock. The sampling bounds exclude oscillator calibration, pin thresholds, monitor propagation and load uncertainty. The on-board runtime identified itself as MicroPython `1.30.0-preview`. The tagged source explains target FIFO handling, and the recorded pins establish what this installed build did. [MicroPython target operations](https://docs.micropython.org/en/v1.29.0/library/machine.I2CTarget.html) · [Tagged RP2 implementation](https://github.com/micropython/micropython/blob/v1.29.0/ports/rp2/machine_i2c_target.c) · [NXP UM10204, clock stretching](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)

## Retained failure and recovery

One admission attempt found a visitor before selection and stopped. The next session completed three captures and the fourth program readback. Its late first reply raised SCL after HALT while SDA stayed low. Disconnecting the native target returned both lines high, but enabling it for the next trial brought SDA low again. The idle check stopped before launching that transaction. Both FPGA commands had already been released in the preceding capture. This sequence shows why a retry must verify idle with the target **connected**. The internal peripheral state causing the low was not directly observed. [Admission receipt](sessions/boundary-a.json) · [Failed session receipt](sessions/boundary-b.json) · [Partial physical capture](sessions/boundary-b.bin.gz)

The corrected harness reset only the RP2350B I2C1 block with its SDA/SCL disconnected before each trial and after capture. The three subsequent six-trial sessions completed, including four immediate reads after late replies in the two boundary sessions. A receiver reset isolates these trials. Automatic bus recovery by the firmware remains untested. All five sessions that selected the FPGA image restored the stock factory configuration. The first physical acquisition started at 21:40:05 UTC and the last ended at 21:48:00 UTC on 25 November 2026. All runs used the same board, native target, fixture, timebase and decoder. [Session receipts and terminals](sessions/) · [RP2350 reset bit](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2350/hardware_regs/include/hardware/regs/resets.h) · [SDK I²C reset sequence](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2_common/hardware_i2c/i2c.c)

The 24-trial table covers four full sessions. The three scored traces from the failed session are stored separately. Every trial in the table cold-loaded and verified all 384 or 432 program bytes and the request registers. The same archived E0059 FPGA image ran both loads. Its native and linked pad controls read `0x5A` in every trace. Neither this receiver nor the public board supplied a calibrated voltage waveform. The supply, pull-up resistance, branch capacitance, receiver threshold and probe skew still need measurement. [Earlier receiver crossover](../E0060-i2c-receiver/README.md) · [50 MHz digital cases](../E0058-i2c-guard/README.md) · [Western Cape bench parts](../../docs/research/western-cape-bench.md)

## Replay and acquisition

From the H: checkout, replay the retained evidence with the project workbench. The offline audit rebuilds the jobs and cold-load plans, checks file identities, decodes the raw samples and rejects five altered observations. The first job body is retained at commit `ed57e29`. The standard-library Windows interpreter could score raw traces directly. Rebuilding the historical assembler transform also imports cocotb, which the pinned workbench supplies. [Input and artifact hashes](manifest.json) · [Audit](audit.py) · [Exact executed jobs](jobs/)

The pinned workbench passed `make doctor` and `make check`. The production profile still matched all twenty qualified inputs. The wheel download below reproduced the archived SHA-256. [Project check logs](checks.json)

```powershell
$repo = (Resolve-Path .).Path
$scratch = (New-Item -ItemType Directory -Path (Join-Path $repo ("build/receiver-stretch-" + (Get-Date -Format yyyyMMdd-HHmmss-ffff)))).FullName
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$mounts = @('run','--rm','--mount',"type=bind,source=$repo,target=/workspace,readonly",
    '--mount',"type=bind,source=$scratch,target=/workspace/build",'--tmpfs','/tmp:exec','-w','/workspace',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace')
docker @mounts --network none $image python3 -B evidence/E0064-i2c-target-stretch/audit.py
docker @mounts --network none $image make check
```

To acquire new data, use a fresh output directory for each call. The visitor runner requires board 4 to be idle with the archived image already available. The run can stop before selection if a visitor arrives. The wheel's SHA-256 is checked on entry. The four successful archived sessions can be replayed without a board or a wheel.

```powershell
docker @mounts $image python3 -m pip download --no-deps --only-binary=:all: --dest build websockets==15.0.1 --platform any --python-version 3.11 --implementation py --abi none
$wheel = 'build/websockets-15.0.1-py3-none-any.whl'
docker @mounts $image python3 -B experiments/remote_i2c/stretch/run.py core build/core --wheel $wheel
docker @mounts $image python3 -B experiments/remote_i2c/stretch/run.py boundary build/boundary --wheel $wheel
docker @mounts --network none $image python3 -B experiments/remote_i2c/stretch/score.py boundary build/boundary/terminal.bin.gz
```
