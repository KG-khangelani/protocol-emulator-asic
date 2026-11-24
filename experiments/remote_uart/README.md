# Run the UART on a public FabricFox from Docker

## Separate transmitter and receiver oscillators

Use the oscillator fixture on the Welland PMOD HAT. The FPGA clocks the released UART receiver from its own HFOSC. The RP2350 transmits from its crystal-derived system clock. GPIO26 carries the UART on the original UIO1 pad. GPIO29 samples the returned FPGA clock on UIO4. GPIO16 supplies one strobe per loader transaction and stays high throughout reception. The loader stages data through the dedicated input bus and returns bytes on the dedicated output bus. It releases the HAT-linked UI1 driver before the peer takes UIO1. [Board wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Fixture correction](../../evidence/E0054-separate-oscillators/wiring-correction.md)

From the project checkout on H:, run this PowerShell command for each available board. The client checks the board's occupancy and bitstream hash, runs the test in controller RAM, then restores the previous gallery selection. Each run directory contains the complete terminal response, both captured signals and the host verdict.

```powershell
$repo = (Get-Location).Path
$output = New-Item -ItemType Directory -Force (Join-Path $repo 'build/remote-uart')
$run = 'build/' + [Guid]::NewGuid().ToString('N')
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
docker run --rm --mount "type=bind,source=$repo,target=/workspace,readonly" --mount "type=bind,source=$($output.FullName),target=/workspace/build" --tmpfs /tmp -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $image python3 -B experiments/remote_uart/run.py --suite oscillator --board fpga-1 --out $run
```

Inside the locked workbench, rebuild the diagnostic configuration with `python3 -B experiments/fpga_uart/build_oscillator.py --out build/fresh-oscillator`. For the offline board audit use `python3 -B evidence/E0054-separate-oscillators/audit.py`. [Measurements and claim limits](../../evidence/E0054-separate-oscillators/README.md)

## Earlier shared-clock experiments

The E0052 and E0053 commands below record the earlier setup. Their pin captures and host-service times remain available for offline replay. The HAT joins three pairs of selector and bidirectional pins. Those runs did not measure current on the shared connections. Use the isolated fixture above for live Welland measurements. [Historical physical evidence](../../evidence/E0052-remote-uart/README.md) · [Historical baud-offset evidence](../../evidence/E0053-uart-baud-offsets/README.md)

The original Docker client loads the E0051 FPGA configuration and runs a short
MicroPython test in the public board's RP2350 RAM. Two physical signals cross
from the RP2350 to the FPGA on the demo PCB. GPIO16 supplies the project
clock and GPIO26 carries the UART waveform on UIO1. The controller also
reads back the program and receives both result bytes over the public pins.
The service exposes the same bitstream gallery and serial terminal to a
browser. [Public board list](https://tinytapeout.fpgas.online/) · [Provider's upload instructions](https://docs.fpgas.online/en/latest/user/boards/tt-fpga/own-bitstream.html)

From an H: checkout with the project workbench installed, choose an available
public FPGA slug. The command checks occupancy and the current design before
using it. The upload is the existing public project bitstream. The service
retains its gallery copy until eviction or reboot. The test releases its
GPIO drivers and restores the original RP2350 frequency and board control
mode. No board firmware installation is required.

```powershell
$repo = (Get-Location).Path
$output = New-Item -ItemType Directory -Force (Join-Path $repo 'build/remote-uart')
$run = 'build/' + [Guid]::NewGuid().ToString('N')
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
docker run --rm --mount "type=bind,source=$repo,target=/workspace,readonly" --mount "type=bind,source=$($output.FullName),target=/workspace/build" --tmpfs /tmp -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $image python3 -B experiments/remote_uart/run.py --board fpga-1 --out $run
```

The network connection reaches the provider and retrieves the hash-checked
`websockets` 15.0.1 wheel from PyPI. To reuse a local copy, supply
`--wheel build/websockets-15.0.1-py3-none-any.whl` with the file in the
mounted output directory. The output contains a receipt, the board terminal
text and its original raw REPL response. The provider may be occupied or
offline on a later visit. The existing container-only FPGA rehearsal also
runs with networking disabled. [Offline build and pin simulation](../fpga_uart/README.md) · [Terminal library](https://pypi.org/project/websockets/15.0.1/)

## Physical measurements

The program in the FPGA is loaded from the archived 76-clock cold-start
sequence. After readback the RP2350 uses its hardware PIO for the entire
clock and 8N1 waveform. Sixteen idle clocks precede the first start, followed
by 434 clocks per serial bit, LSB first. A separate PIO machine observes
100,000 periods on the physical clock pad. The two pins share the RP2350
timebase. A native host loop reads valid, data and status with a selector
dwell of at least 3 µs. It accepts only a ready `A7` terminal with a saved
first byte. GPIO sampling, framing controls and timers run on the board,
so Internet latency is outside the service interval. [Firmware GPIO map](https://github.com/TinyTapeout/tt-micropython-firmware/blob/baaf0a2758b475d6e099b8ef65dbd1b5667ea0aa/src/ttboard/util/platform/rp2350.py) · [PIO state machine](https://docs.micropython.org/en/latest/library/rp2.StateMachine.html) · [RP2350 SIO offsets](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2350/hardware_regs/include/hardware/regs/sio.h) · [Timer registers](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2350/hardware_regs/include/hardware/regs/timer.h)

The host checks the largest recorded inter-poll gap plus the largest read
sequence plus 2 µs for timer quantization. At 12.5 MHz the limit is 347.2 µs.
The first two program-byte reads provide driven-high and driven-low UIO1
controls. A third observation samples the requested release. Each applies
only the MCU's weak pull-down and then pull-up. These digital readings can
leave driver ownership unresolved. Measuring release time or current needs a
calibrated receiver-end fixture. [Bench contract](../../docs/research/council-2026-11-24/next-experiments.md#3-measure-one-claimed-external-interface)

## Baud-offset and launch-delay trials

From the repository root on the Windows host, this runs the two-frame rate and phase matrix on an idle public FabricFox. Use another available board slug to repeat it. The script checks the E0051 bitstream and the released receiver before contacting the board. Each invocation creates a new output directory.

```powershell
$repo = (Get-Location).Path
$output = New-Item -ItemType Directory -Force (Join-Path $repo 'build/remote-uart')
$run = 'build/' + [Guid]::NewGuid().ToString('N')
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
docker run --rm --mount "type=bind,source=$repo,target=/workspace,readonly" --mount "type=bind,source=$($output.FullName),target=/workspace/build" --tmpfs /tmp -w /workspace -e PYTHONDONTWRITEBYTECODE=1 $image python3 -B experiments/remote_uart/run.py --suite margin --board fpga-1 --out $run
```

The board captures GPIO26 every two RP2350 ticks with DMA while the original register reader services the FPGA. Each of the twelve trials records its complete packed bit samples in `samples_hex`, least significant bit first within each byte. The clock generator, peer and digital sampler share one oscillator. The client checks the pad transitions from the intended bits and compares the FPGA's separate delivery and status observations against the case criteria. The full raw REPL response is saved as `terminal.bin` and the host verdict as `result.json`. [Frozen matrix](../../docs/decisions/0055-measure-physical-uart-baud-offsets.md) · [Audited results](../../evidence/E0053-uart-baud-offsets/README.md) · [MicroPython DMA](https://docs.micropython.org/en/latest/library/rp2.DMA.html)
