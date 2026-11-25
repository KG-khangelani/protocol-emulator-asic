# E0065 — What two physical SPI inputs see after MISO disable

**On FabricFox board 4 both receiver pins still read the preceding MISO bit at all 24 reselections with the weak pull set against that bit.** The FPGA had already commanded its driver off. All 60 fresh transactions returned the correct opposite-command reply. The first observed change toward an opposing bias came at least 952 ns after the disable command, even with pulls on both inputs. The calibrated target-branch turnoff time remains unknown. These results apply to the 126-word SPI target on this 12.5 MHz FPGA fixture. [Prospective decision D67](../../docs/decisions/0067-test-miso-bias-at-both-receiver-inputs.md) · [Measurements by trial](measurements.json.gz)

## Known levels, transactions and sampling

The Welland HAT connects UIO3 and UI3 through Raspberry Pi GPIO11. This gives two observations of the same branch on the resident RP2350B, GPIO28 at JB4 and GPIO20 at JA4. GPIO29 carries a copy of the net commanding the FPGA's MISO output enable. The board jobs set GPIO20 and GPIO28 as inputs, read back the pad pulls, the SIO function and the disabled output-to-pad states, and checked host output enables before starting. Each PIO sample captured both receiver pins together with SCK, MOSI, CS, enable, HALT and the project clock. Absolute time uses a nominal shared 125 MHz clock, with one sample per 8 ns and uncharacterized channel skew. Both runs used the same physical board, host and requester. [Provider pin map](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [RP2350 pad fields](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2350/hardware_regs/include/hardware/regs/pads_bank0.h) · [RP2350 GPIO status](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/rp2350/hardware_regs/include/hardware/regs/io_bank0.h) · [Mapped FPGA enable and configuration](../E0057-remote-spi/README.md#fixture-clocks-and-measurement-limits)

Two sessions reversed both the bias and case order. Each ran 50 trials spanning five bias settings, both commands, a held abort, a selected clock stall and three abort/reselection gaps. The original first bit was low for `A4 → 3C` and high for `A5 → A7`. Both inputs read it correctly in the last four enabled samples in all 100 trials. The requested SCK half-period was 1 µs. SCK was high at the sampled abort. This slice of the earlier matrix fixes the first response bit and requester phase. The full E0057 sweep supplies the other phases, polarities, bits and speeds. [Schedules and cold-load preparation](../../experiments/remote_spi/branch_bias/run.py) · [Earlier sweep](../E0057-remote-spi/README.md#how-much-time-the-requester-left-between-selections)

| Event | Trials | Observed on this board |
| --- | ---: | --- |
| CS rose during a driven reply | 80 | The FPGA enable witness fell 392 ns after CS rose in every trial. In the 20 held aborts, CS and SCK stayed high and enable stayed low. |
| CS selected a fresh transaction | 60 | Requested gaps of 400, 424 and 480 ns measured 408, 424 and 488 ns. The respective minimum intervals from observed disable to fresh CS, reduced by one sample, were 8, 24 and 88 ns. Both pins decoded all 60 new replies with the E0057 setup/hold checks and terminal status `B9`. |
| Selected SCK stopped | 20 | The enable witness fell 5.544 or 5.624 µs after the last SCK edge. HALT followed at 5.624 or 5.704 µs. All 20 reached status `BB` while CS remained asserted through timeout. |
| No-pull historical comparison | 10 matched schedules × 2 runs | Fresh bytes, terminal status, abort/timeout timing and applicable clearance, setup and hold matched the original GPIO28 captures. |

The 100 acquisitions contain 692,080 simultaneous samples. For each of the 40 opposing-bias trials the table gives the interval from observed disable to the first sample in the *last uninterrupted run* of the imposed level before the next drive or the end of capture. The number of transitions includes every observed level change through that interval of released operation. A finite observation never establishes indefinite stability. [Offline scorer](../../experiments/remote_spi/branch_bias/score.py) · [Raw forward](forward/terminal.bin.gz) · [Raw reverse](reverse/terminal.bin.gz)

| Opposing bias | Finite results per pin | GPIO20 sustained level after disable | GPIO28 sustained level after disable | GPIO28 transitions per trial |
| --- | ---: | ---: | ---: | ---: |
| Up on GPIO28 | 10/10 | 2.104–2.200 µs | 2.360–2.520 µs | 25–29 |
| Up on both | 10/10 | 1.368–1.400 µs | 1.480–1.560 µs | 15–17 |
| Down on GPIO28 | 8/10 | 10.224–11.488 µs | 16.400–33.520 µs | 126–697 |
| Down on both | 10/10 | 2.720–3.024 µs | 3.680–3.920 µs | 43–45 |

With a single opposing pull-down, both held-abort captures ended 10.480 µs after disable. GPIO20 still read high and GPIO28 was changing. These two observations are right-censored. Across all opposing trials GPIO20 changed 38 times and GPIO28 changed 4,176 times. Across the 40 matching-bias trials the counts were 0 and 2,788 respectively. With no pulls they were 10 and 578 in 20 trials. Weak-bias levels cannot establish whether a driver was sourcing or sinking current at fresh CS. The earlier 424 ns minimum over all E0057 cases was 8 ns. The 24 ns at that gap above applies only to the selected phase and bit.

## Does the running project clock affect the observed transitions?

The first single-pull-down A5 held-abort capture placed all 126 GPIO28 transitions in three of ten sample phases. Before the third acquisition we recorded a control that parked the FPGA clock while the requester and sampler continued running. It used the same configuration, bias and abort, and returned every raw 16-bit DMA sample, bypassing the transition encoder. Two counterbalanced blocks supplied four matched parked/continuous pairs. The recorded clock stopped low for 8.056 µs starting 8.912 µs after observed disable. CS and SCK stayed high, MOSI stayed fixed and enable stayed low. Each trace covered 51.2 µs. We removed two samples at either edge of each comparison window, leaving 1,003 samples. [Control specified before acquisition](../../experiments/remote_spi/branch_bias/clock-control.md) · [Raw snapshots](clock/terminal.bin.gz) · [Clock-window decoder](../../experiments/remote_spi/branch_bias/clock_score.py)

| Condition | Traces | Clock edges in middle window | GPIO28 edges before / during / after | GPIO20 edges in middle |
| --- | ---: | ---: | --- | --- |
| Continuous project clock | 4 | 200 each | 56–86 / 200 / 200 | 0 after a prior zero, 1 after a prior one |
| Parked project clock | 4 | 0 each | 56–86 / 0 / 200 | 0 after a prior zero, 1 after a prior one |

The repeated transitions at GPIO28 depended on project-clock activity on this fixture. GPIO20 recorded only the single high-to-low change where an opposing pull-down was expected. These raw controls rule out the transition encoder as the sole explanation. They leave the coupling path, pad voltages, actual pull strength and target branch current unresolved. In particular the GPIO28 count cannot be used as a voltage-crossing count or timestamp of electrical turnoff.

## Records and verification

All three jobs used the configuration selected in E0057 (`d4b92016…dae5b`) and verified the exact 504 firmware bytes (`e5d25fc5…c9e58`), register values `7E`, `3C` and `A7`, and 1,050 loader steps after an intentional wrong-byte detection. The public gallery provided the existing configuration. Each session saw zero prior clients and restored the factory project. The first development decoder rejected the newly recorded eighth signal with `transition order`, since E0057 admits seven bits. The eight-input decoder replays the original recordings and sends each input separately through the historical SPI checks. The ten archived no-pull schedules and the third uncompressed acquisition check that change. [FPGA image](../E0057-remote-spi/fabricfox-spi.bin) · [Firmware](../../experiments/spi_target/watchdog/target.asm) · [Acquisition and source digests](manifest.json)

| Session | Actual UTC, 25 November 2026 | Records |
| --- | --- | --- |
| Forward | 21:59:34–22:00:07 | [Receipt](forward/result.json) · [Executed job](forward/job.py.gz) |
| Reverse | 22:00:40–22:01:14 | [Receipt](reverse/result.json) · [Executed job](reverse/job.py.gz) |
| Raw clock control | 22:03:58–22:04:30 | [Receipt](clock/result.json) · [Executed job](clock/job.py.gz) |

The first acquisition began at 23:59 SAST on 25 November and the last finished at 00:04 SAST on 26 November. `make doctor` and `make check` passed in the locked workbench, including 163 unit tests. Replay checks all 20 production files, rebuilds the three executed jobs byte-for-byte, compares measurements against the retained values and rejects five damaged inputs. These inject a host driver, truncate the raw DMA record, mislabel a running clock, invert GPIO20 before abort, and duplicate a transition time. [Workbench checks](checks.json) · [Offline audit](audit.py)

## Next electrical measurement

Use the named RP2040 requester and the Lattice breakout. First calibrate driven-high, driven-low and released controls under both limited bias polarities on the measured, loaded branch. Capture CS, output enable, and the voltages on each side of a measured 470 Ω series resistor on deskewed channels. Reproduce the 480 ns handoff first, then 424 ns, 400 ns and the application's earliest peer use. Bound the time from CS to the end of target drive using the reference-state current bands and the fixture's own response. Accept a handoff only when that upper bound precedes peer use and the correct fresh byte is delivered with the temporary bias removed. Overlapping uncertainty bands leave the point indeterminate. For diagnosing GPIO28, acquire the project clock and both endpoint voltages on the same timebase. Allow 2–4 equipped hours for reference measurements and 3–6 for the SPI matrix. [Fixture method and uncertainty](../E0049-review-council/panel-b/fixture/bench.md) · [Local header map](../E0063-local-breakout/README.md) · [Western Cape parts and instruments](../../docs/research/western-cape-bench.md)

## Reproduce

Offline replay works from the repository root with Python 3.11 or later.

```powershell
python -B evidence/E0065-spi-branch-bias/audit.py
```

For Docker Desktop, bind a fresh H: directory for output. The first command in the second block reruns the archive offline. The other commands exercise the public board using the existing gallery entry when free.

```powershell
$repo = (Resolve-Path .).Path
$scratch = (New-Item -ItemType Directory -Path (Join-Path $repo ("build/spi-bias-" + (Get-Date -Format yyyyMMdd-HHmmss-ffff)))).FullName
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$mounts = @('run','--rm','--mount',"type=bind,source=$repo,target=/workspace,readonly",
    '--mount',"type=bind,source=$scratch,target=/workspace/build",'--tmpfs','/tmp:exec','-w','/workspace',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace')
```

```powershell
docker @mounts --network none $image python3 -B evidence/E0065-spi-branch-bias/audit.py
docker @mounts $image python3 -m pip download --no-deps --only-binary=:all: --dest build websockets==15.0.1 --platform any --python-version 3.11 --implementation py --abi none
$wheel = 'build/websockets-15.0.1-py3-none-any.whl'
foreach ($order in 'forward','reverse','clock-control') {
    docker @mounts $image python3 -B experiments/remote_spi/branch_bias/run.py $order "build/$order" --wheel $wheel
    if ($LASTEXITCODE -ne 0) { break }
}
docker @mounts --network none $image python3 -B experiments/remote_spi/branch_bias/score.py build/forward/terminal.bin.gz
docker @mounts --network none $image python3 -B experiments/remote_spi/branch_bias/clock_score.py build/clock-control/terminal.bin.gz
```
