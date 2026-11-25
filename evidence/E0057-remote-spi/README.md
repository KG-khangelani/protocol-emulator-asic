# E0057 — Physical SPI abort, reselection and selected-clock timeout

On 25 November 2026, Welland FabricFox board 4 ran the 126-word E0056 SPI target against an external RP2350 requester. **At the original deadlines, the 12.5 MHz FPGA passed 0/384 complete abort handoffs and 0/32 selected-clock timeouts.** At four times the requester durations, all 384 fresh bytes were valid and all 32 stalls timed out within 8 µs. Moving the abort 32 ns later also fixed ten pre-abort bit failures. In a separate 1,408-trial sweep the shortest tested gap with positive digital clearance in every case was **424 ns**. The **480 ns** point gave at least **56 ns** clearance in two separate runs. [Decision and prospective criteria](../../docs/decisions/0059-exercise-spi-recovery-on-fabricfox.md) · [Decoded measurements](summary.json)

Board 4 had no connected client at initial inspection. Board 1 had one. Both advertised a digital terminal, camera and visitor FPGA upload. Neither published an accessible calibrated probe or a current discriminator on this MISO branch. The board data below measure when the FPGA commanded MISO off and what digital level the RP2350 sampled. The absolute time when the MISO driver stopped sourcing or sinking current remains open. [Dated fixture inventory](access.json) · [Provider pin map](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Visitor board controls](https://docs.fpgas.online/en/latest/user/boards/tt-fpga/own-bitstream.html)

## What the board did

| Requester on the 12.5 MHz board | Complete abort handoffs | Timeout while selected | Relevant observations |
| --- | ---: | ---: | --- |
| Original durations, SCK 0.5–2 MHz, 160 ns CS-high and 2 µs timeout limit | 0/384 | 0/32 | The witness was active at 382 new selections. Only 101 fresh bytes met the bit and setup/hold checks. All 32 timeout markers arrived after SCK had resumed, 10.528–14.280 µs after the start of the stall. |
| Four times the durations, SCK 0.125–0.5 MHz, 640 ns CS-high and 8 µs timeout limit | 374/384 | 32/32 | All fresh command prefixes had MISO disabled. All 384 replies met setup and hold. The witness fell 264–416 ns after abort. Timeouts occurred at 5.544–5.984 µs. |
| Same slower requester, abort 32 ns later, same 640 ns handoff | 384/384 | Separate abort-only run | All 384 pre-abort bits, release deadlines, fresh command prefixes, replies and terminal states passed. The witness again fell 264–416 ns after abort. |

The check uses both commands (`A4 → 3C`, `A5 → A7`), eight response-bit positions, stopped-high and stopped-low SCK, four programmed launch phases and three ordinary SCK periods. A fresh transaction requests the opposite command. Each selected-stall case holds CS low while SCK pauses. The decoder compares the observed edges of SCK, MOSI and CS with the requester schedule, checks previously sampled response bits, decodes the fresh response, applies setup/hold limits of 60/40 ns or 240/160 ns, and checks the terminal status. Four programmed phases can quantize to fewer distinct times on the 8 ns grid. The original-rate run extended the observation tail by 12 µs to distinguish a late marker from a missing one. [Original requester](../../experiments/spi_target/requester.py) · [Physical decoder](../../experiments/remote_spi/check.py)

On the initial slower matrix the ten misses were all low-clock aborts. The expected bit reached the sampler on the same sample as the CS rise four times, one sample later three times and two samples later three times. Every fresh byte still passed, with conservative digital setup of at least 416 ns and hold of at least 1,256 ns. The later-abort run changed the scheduled spacing from the previous SCK edge from 560 to 592 ns. The archive retains the original failures. [Ten named counterexamples](summary.json) · [Initial matrix pins](board-4/matrix/terminal.bin.gz) · [Later-abort pins](board-4/settled/terminal.bin.gz)

At the original wall-clock rate, the two ordinary accepted commands produced sampled bytes `1C` and `E7` in place of `3C` and `A7`, despite both ending with the success marker. The invalid `00` control correctly rejected the prefix. Across the 384 aborts, 360 trials had active drive before CS rose. None of those had an enable fall within 160 ns, including the one-sample allowance. The other 24 lacked an active driver to time immediately before abort. This comparison runs the actual FPGA at its accepted clock. The earlier 50 MHz RTL and submitted-netlist results apply to their own test conditions. [Original-rate raw capture](board-4/wall/terminal.bin.gz) · [E0056 model and netlist results](../E0056-spi-target-watchdog/README.md)

## How much time the requester left between selections

At the fastest slower setting, SCK had a 1 µs half-period. Each gap covered 128 cases spanning both commands, eight abort bits, two clock levels and four launch phases. If SCK was high, the requester returned it low halfway through the gap. The first sweep compared both pre-abort offsets. A second sweep tested the later abort in descending 8 ns steps. Clearance is the interval between the witnessed output-disable edge and the next CS assertion, reduced by one sampling interval. Zero, a same-sample transition, or residual enable at reselection fails the positive-clearance requirement. Channel skew remains uncalibrated. [Coarse sweep](board-4/gaps/terminal.bin.gz) · [Fine sweep](board-4/fine/terminal.bin.gz)

| Requested CS-high gap, later abort | Full functional passes | Full passes with positive digital clearance | Lowest digital clearance |
| ---: | ---: | ---: | ---: |
| 160 ns, coarse | 0/128 | 0/128 | −264 ns |
| 320 ns, coarse | 53/128 | 44/128 | −104 ns |
| 400 ns, fine | 119/128 | 112/128 | −24 ns |
| 408 ns, fine | 128/128 | 112/128 | −8 ns |
| 416 ns, fine | 128/128 | 119/128 | −8 ns |
| 424 ns, fine | 128/128 | 128/128 | 8 ns |
| 480 ns, coarse and fine | 128/128 in each | 128/128 in each | 56 ns in each |
| 560 and 640 ns, coarse | 128/128 at each | 128/128 at each | 136 and 216 ns |

All eight gaps from 424 through 480 ns in the fine sweep passed with positive clearance in every case. The nominal 424 ns gap measured 416–432 ns across trials. The nominal 480 ns gap measured 472–488 ns. The earlier abort offset continued to miss six pre-abort bit checks per 128-case group at 480, 560 and 640 ns. At both offsets, **every fresh reply byte in the coarse sweep was correct**, including the groups with stale drive into the new command. A fresh byte alone cannot score bus ownership. For a repeat on this fixture, 480 ns provides a directly observed margin larger than the sampler interval. A requester or load with different timing needs its own measurement. [All 25 coarse and fine gap groups](summary.json)

## Fixture, clocks and measurement limits

The FPGA fixture uses the five qualified RTL sources, the previously exercised four-lane FPGA program RAM adapter and the board pin constraints. Two independent seed-10 builds yielded the same 104,090-byte bitstream. Both strict 50 MHz routes failed internal timing at an estimated 13.768 MHz. Both 12.5 MHz routes passed at that estimate using 1,780/5,280 logic cells and four block RAMs. The run used 12.5 MHz. The mapped design check confirms that the signal driving the MISO `SB_IO.OUTPUT_ENABLE` is also the data input of the dedicated witness pad. [First route](route-a.json) · [Second route](route-b.json) · [50 MHz router report](route-50-timing.json.gz) · [12.5 MHz router report](route-12.5-timing.json.gz) · [FPGA fixture](../../experiments/remote_spi/fabricfox.v)

| Captured signal | FabricFox pin | RP2350 GPIO |
| --- | --- | ---: |
| SCK, MOSI, CS | UIO0, UIO1, UIO2 | 25, 26, 27 |
| Physical MISO pad | UIO3, iCE40 pin 6, JB4 | 28 |
| MISO output-enable copy | UIO4 | 29 |
| HALT | UIO5 | 30 |
| Project-clock copy | UIO6 | 31 |

UIO3 and UI3 share Raspberry Pi GPIO11 on the HAT. After load, the RP2350 releases the linked selector pins and samples GPIO28 as an input. The target's synchronized self-read of MISO comes from the physical input of the bidirectional pad. The observer samples seven pins together every nominal 8 ns with PIO and DMA. The requester, observer and FPGA clock generator share the RP2350's 125 MHz timebase. The decoder checks the continuity and period of the observed 12.5 MHz clock in every trial. These runs characterize one FPGA, one board load and related clocks. Independent-clock behavior and ASIC pad timing require their own fixtures. [Board wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [PIO and DMA payload](../../experiments/remote_spi/on_board.py) · [MicroPython DMA](https://docs.micropython.org/en/latest/library/rp2.DMA.html)

All six sessions deliberately corrupted the second programmed byte and observed the wrong value on readback. Each then cold-loaded and read back all 504 correct bytes and the three length/TX register values (`7E`, `3C`, `A7`). The executable program is the exact E0056 binary with SHA-256 `e5d25fc51d17684ede5615ece99501084c69380091c61c9ea58aba65b23c9e58`. Each schedule starts with an executor rearm. Between an abort and its fresh frame the firmware acts autonomously. HALT and enable were sampled continuously for terminal timing and stability. The requester read the terminal code once from dedicated output pins at the end of the capture. [Firmware](../../experiments/spi_target/watchdog/target.asm) · [Retained configuration](fabricfox-spi.bin)

## Session and verification records

The six board sessions ran on 25 November from 17:29:03 to 17:40:22 UTC (19:29:03–19:40:22 SAST). The archive holds 4,433 physical trials and 44,290,632 simultaneous sample instants. The pilot captured nine complete traces and restored MCU clock and pin ownership. The first gallery restoration request returned HTTP 404 because the idle display is managed by the provider's daemon. Later sessions selected the factory startup demo on exit. At 17:41:34 UTC the gallery reported `idle_display`, the daemon reported `loaded`, and board 4 had zero clients. Board 1 still showed one client. The public gallery retained the one experiment bitstream under `tt_um_khangelani_spi_d4b92016`, bringing its upload count from eight to nine. Each upload receipt reported zero evictions. [Pilot receipt with the error](board-4/pilot/result.json) · [Final board state](restoration.json) · [Provider idle procedure](https://github.com/fpgas-online/fpgas.online-tt/blob/main/README.md)

The Linux workbench passed `make doctor` and `make check` (163 tests). An intermediate check finished its unit tests but the input-integrity guard detected that the new experiment scripts had changed during the run. The subsequent check ran with stationary inputs and passed. The offline audit regenerates all six measurement tables, rehashes the 20 qualified physical inputs against both release tags and rejects six altered captures covering missing SCK, missing project clock, stale drive, wrong MISO data, wrong terminal status and corrupt program readback. [Doctor](doctor.log.gz) · [Interrupted check](interrupted-check.log.gz) · [Completed check](check.log.gz) · [Audit](audit.py) · [Artifact and source digests](manifest.json)

## Reproduce

Run the offline audit from the repository root with both release tags available.

```powershell
python -B evidence/E0057-remote-spi/audit.py
python -B experiments/remote_spi/check.py evidence/E0057-remote-spi/board-4/wall --report-only
```

The second command lists individual failing cases. Omitting `--report-only` makes that command return a failure for the original-rate run. The earlier E0056 simulation archive has its own replay command in its report. The following Docker Desktop commands use a fresh H: output directory to rebuild the FPGA fixture and run a physical capture.

```powershell
$repo = (Resolve-Path .).Path
$scratch = (New-Item -ItemType Directory -Path (Join-Path $repo ("build/spi-replay-" + (Get-Date -Format yyyyMMdd-HHmmss-ffff)))).FullName
$image = 'protocol-emulator-asic-workbench:2026-07-29'
$mounts = @('run','--rm','--mount',"type=bind,source=$repo,target=/workspace,readonly",
    '--mount',"type=bind,source=$scratch,target=/workspace/build",'--tmpfs','/tmp','-w','/workspace',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace')
docker @mounts --network none $image python3 -B experiments/remote_spi/build.py build/route
docker @mounts $image python3 -B experiments/remote_spi/remote.py --board fpga-4 --suite matrix --image build/route/image.bin --out build/matrix
docker @mounts --network none $image python3 -B experiments/remote_spi/check.py build/matrix --report-only
```

The public runner checks board occupancy and the expected configuration digest, uses the visitor gallery and restores its selection through the SDK startup design. Each suite requires a fresh output directory. Other suite names are `pilot`, `settled`, `gaps`, `wall` and `fine`. The first networked run fetches a digest-checked WebSocket wheel unless `--wheel` points to a local copy. The manifest records the tested container identity. [Build command](../../experiments/remote_spi/build.py) · [Board runner](../../experiments/remote_spi/remote.py) · [Public workbench package](../../docs/submission.md)

## Next electrical test

Budget one instrumented bench session with a named SPI requester and declared supply, board, branch load and CS-high requirement. Use switchable, characterized current-limited loads and a calibrated current or differential-voltage measurement on the MISO target branch. Before running SPI, demonstrate that the setup distinguishes actively driven high, actively driven low and commanded high impedance for both bias polarities. Record instrument identifiers, calibration, sample rate, interchannel skew, load and the measured uncertainty.

Capture CS, the enable witness and the MISO branch together for both previously driven levels. Repeat the 400, 424 and 480 ns cases and the application's shortest allowed gap. Accept only if the upper uncertainty bound on driver turnoff precedes the peer's earliest bus use and every opposite command returns its correct byte. Reject that operating point if active drive overlaps use, the control states overlap within uncertainty, or the fresh transfer fails. Budget the 160 ns criterion only if the actual requester requires it. [Council electrical and architecture experiments](../../docs/research/council-2026-11-24/next-experiments.md)
