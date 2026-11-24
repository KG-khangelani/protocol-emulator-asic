# SPI release, reselection and missing-clock comparison

**The revised 120-word VM program released MISO in 61–99 ns and served the opposite command in all 384 modeled abort/reselect trials. It missed the 2 µs timeout in all 32 selected-clock pauses.** The original 59-word program passed those 32 pauses and failed all 384 complete reselections. A 32-word RP2040 PIO program returned both full reply bytes under normal clocks. It also missed the combined release and reselect requirement. Each implementation encountered a concrete counterexample to the council's full role. Keep the SPI target experimental. [Predeclared comparison](../../docs/decisions/0057-compare-spi-target-firmware.md) · [Complete scoreboard with first failures](summary.json)

## UART probe access

The Welland service reported `fpga-1` and `fpga-4` online and idle at 23:03 UTC on 24 November (01:03 SAST on 25 November). Both device identity hashes matched the two E0054 boards. Their live pages exposed a camera, the Commander and bitstream upload. The published wiring puts the project's UART pin on FPGA pin 4, RP2350 GPIO26 and JB2. The HAT joins JB2 and JA2 on Raspberry Pi GPIO10. The public hardware and service descriptions supplied no remotely selectable differential probe on the FPGA branch, characterized sense resistor, probe calibration or measured channel skew. Access was checked with HTTP GET. [Dated board receipts](probe-access.json) · [Provider wiring](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Public service controls](https://docs.fpgas.online/en/latest/setup/tinytapeout.html)

In E0053 the weak-pull readings were identical for driven high and commanded release. E0054's diagnostic FPGA intentionally kept the UART pad input-only. Neither observation times driver turnoff on the load/readback path. A physical verdict needs a fixture that actually drives and releases the target branch, known high, low and high-impedance controls, and a bound on the loaded probe response in both polarities. UART electrical release remains unmeasured. [Weak-pull controls](../E0053-uart-baud-offsets/README.md#remote-instrument-access) · [Diagnostic wiring](../E0054-separate-oscillators/README.md#earlier-failures-and-claim-limits) · [Calibration procedure](../E0049-review-council/panel-b/fixture/bench.md)

## Same externally timed requester

The requester scheduled SCK, CS and MOSI independently of each device. An uninterrupted mode-0 transaction sent an eight-bit command and sampled an eight-bit reply. A4 requests 3C and A5 requests A7. MISO must stay released throughout the command, including when a weak-low bus would hide a driven zero. The scorer checks direction and resolved data, 60 ns setup, 40 ns hold, release and the terminal outcome. The 254 invalid opcodes also exercise the council's earlier criterion for reporting the first mismatched prefix bit before the next rising edge. [Original device contract](../E0049-review-council/panel-c/spi-target/spi-target-contract.md) · [Original scoring rules](../E0049-review-council/panel-c/spi-target/spi_target_screen.py) · [Shared requester and scorer](../../experiments/spi_target/requester.py)

| Digital requirement | Original VM | Revised VM | One-SM PIO |
| --- | ---: | ---: | ---: |
| Complete ordinary replies, including uneven periods | 28/28 | 28/28 | 28/28 |
| Minimum setup / hold in those replies | 131 / 311 ns | 151 / 311 ns | 91 / 391 ns |
| Normal release after the final SCK fall | 61–79 ns | 81–99 ns | 141–159 ns |
| Invalid opcodes kept quiet and returned error | 254/254 | 254/254 | 254/254 |
| Invalid opcodes also reported by the first mismatch deadline | 254/254 | 254/254 | 2/254 |
| Held-clock aborts that released correctly by 160 ns | 0/32 | 32/32 | 0/32 |
| Aborts followed by quiet reselection and a correct fresh reply | 0/384 | 384/384 | 0/384 |
| Paused response clock with CS still low, timeout by 2 µs | 32/32 | 0/32 | 0/32 |
| Stuck CS after a complete reply, timeout by 2 µs | 2/2 | 2/2 | 0/2 |

The 384 reselections span two commands, eight driven bit positions, both clock polarities, 0.5/1/2 MHz and four phase offsets (1/7/13/19 ns). CS rose 140 ns into the selected half-cycle. High SCK returned low at +80 ns. The opposite command selected at +160 ns and clocked its first bit 300 ns later. The 32 held-abort controls kept SCK static for the entire 2.6 µs observation. The 32 pause controls kept CS selected while delaying the next edge by an additional 3 µs. These extend the council's 2 µs missing-clock check to each response bit, as proposed in its polling diagnostic. Four further cases covered a missing command clock, late first clock, early command deselection and a separate missing response clock. [Earlier bounded-polling criterion](../E0049-review-council/panel-c/spi-target/spi-abort-diagnostic.md) · [Input edges and endpoints](cases.json.gz)

All 736 schedules ran on all three programs. Fifteen schedules per VM image also ran on the submitted functional G4 netlist. Each netlist public-pin trace matched the RTL for its entire observation. [Original RTL](original.json.gz) · [Revised RTL](revised.json.gz) · [PIO traces](pio.json.gz) · [Original netlist](original-gate.json.gz) · [Revised netlist](revised-gate.json.gz)

## What changed the outcome

- **VM with timed single-pin waits.** In the council's stalled-high A5 case, the original program held MISO for 1,563 ns after CS rose. The timed wait can detect loss of SCK while CS stays asserted. It can also remain blocked on SCK after CS has risen. In the 384 reselections it released by the deadline 24 times and delivered zero valid fresh replies.
- **VM with cooperative polling.** The revised program tests CS and SCK in a short loop, emits the two literal reply bit patterns and branches back to a released command entry when CS rises. The named stalled-high release fell to 83 ns. Across all reselections the worst modeled margin to the synthetic deadline was 61 ns. The loop has no elapsed-time counter. In the named missing-response-clock case the original terminal reported timeout 1,743 ns after the last edge. At the 2 µs deadline the revised target still drove high. It eventually returned success when the late clocks resumed. The same problem appeared on every bit and both clock levels. [Generated VM assembly](revised.asm) · [VM generator](../../experiments/spi_target/revised.py)
- **Single PIO state machine.** The native program sampled the seven-bit common prefix and final select bit, then shifted one of two eight-bit replies. Its edge waits can block before the next CS check. In the named held-high case the scorer observed no release in 2.6 µs. With SCK returned low after 80 ns it observed release after 203 ns and a correct fresh byte, with stale drive at the beginning of that command. The PIO returned the correct fresh byte with sufficient setup and hold in 192 of 384 cases, while every reselection violated at least one ownership requirement. Six of the 32 held-abort cases failed to establish the intended driven value by the abort instant. The PIO sampled the whole prefix before rejecting it, which explains 252 late invalid-command reports. [Native PIO program](../../experiments/spi_target/target.pio) · [Assembled words](target.hex) · [Emulator and pin observer](../../experiments/spi_target/pio.cjs)

## Resources and limits

| Resource | Original VM | Revised VM | RP2040 PIO |
| --- | --- | --- | --- |
| Resident program | 59 × 32 bits, 236 bytes | 120 × 32 bits, 480 bytes, 8 words free | 32 × 16 bits, 64 bytes, full shared instruction bank |
| Cold setup per trial | 498 loader clocks, all 236 bytes read back | 1,000 loader clocks, all 480 bytes read back | 123 MMIO accesses including enable and 32 instruction readbacks |
| Data and state | Two loaded reply bytes, VM PC, loop/shift state | Two loaded bytes verified, replies encoded in program literals, VM PC and GPIO latches | One state machine, X/Y, ISR/OSR, one 32-bit packed constant, TX/RX FIFO used at cold setup, completion IRQ 0 |
| Runtime wiring and service | SCK, MOSI, CS, MISO and two terminal pins | Same six pins | Same six pins, two terminal pins driven from setup, IRQ wait models a halted terminal |

All three used zero host operations after launch, zero external switches and zero native SPI controllers. The original and revised VM programs used the released ISA, production RTL and cold loading sequence. PIO used the official assembler, a pinned rp2040js instruction implementation, and the council's modeled synchronizer and output-delay convention at 50 MHz. The model gives each system a rising edge at 10 ns and then every 20 ns. The PIO fixture advances the input through three sampled slots and exposes the previous output on the next edge. There is no calibrated pad delay, silicon measurement, all-phase proof or matched silicon-area/energy estimate. The 160 ns threshold is a research discriminator. [Image sizes and cold loads](images.json.gz) · [PIO MMIO transcript](pio-host.json.gz) · [RP2040 datasheet, PIO chapter](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf) · [Pinned PIO implementation](https://github.com/wokwi/rp2040js/blob/cab5fae8d72f44dc300dc139fb6e600f95e8031e/src/peripherals/pio.ts)

**Engineering disposition.** Keep both counterexamples as regression tests. A firmware successor must fit all 128 words, preserve the revised program's 384 reselections and restore the original program's 32 selected-clock timeouts. The operating distinction is whether CS rises or stays asserted during the stall. If a named requester needs both deadlines and firmware cannot meet them together, the council's next bounded experiment is a cycle-level model of a wait that also observes CS. Score simultaneous CS/SCK changes, timeout precedence, legacy behavior and the next complete command before considering an RTL change. Physical UART sign-off still requires the equipped branch measurement. [Council experiment and decision criteria](../../docs/research/council-2026-11-24/next-experiments.md#4-compare-architectures-on-an-externally-clocked-target)

## Reproduction

In the locked Linux workbench, run `python3 -B evidence/E0055-spi-target-comparison/audit.py` from the repository root. It reconstructs every schedule, scores the retained transitions, compares the selected netlist and RTL traces, and verifies the twenty physical inputs against both stable releases. Six altered records challenge reply data, a driven-low command pin, release one nanosecond late, a corrupt fresh response, a false timeout outcome and a shifted SCK return. The manifest binds the input programs, tool identities, schedules and retained results. [Audit](audit.py) · [Source hashes and original run times](manifest.json)

For a full execution on H: with Docker Desktop and the locked project workbench, run the command below from the checkout. It fetches hash-checked PIO tools and three functional cell models, then runs the simulations with networking disabled in a fresh directory under `build/`. With previously downloaded inputs, pass `-PioTools` and `-Pdk` with their directory paths. [Rebuild and comparison script](../../experiments/spi_target/replay.ps1)

```powershell
.\experiments\spi_target\replay.ps1
```

A second execution downloaded the tools and models afresh. Its schedules, all five trace sets, PIO MMIO transcript, program metadata, generated VM source and PIO words matched the first run byte for byte. The locked workbench passed `make doctor` and `make check`, including 163 unit tests. The prior E0054 audit also replayed all three independent-clock UART sessions. [Fresh execution receipt](clean-replay.json) · [Tool versions](doctor.log.gz) · [Repository checks](check.log.gz)
