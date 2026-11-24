# E0051 — FabricFox v2 UART configuration and package-pin rehearsal

On 24 November 2026 the host exposed one motherboard serial port and six
Bluetooth serial ports. Its present USB devices, mounted volumes and
instrument configuration identified no project board, independently
isolatable UART peer or capture instrument. BENCH-T01 remains open. The
board-independent part of the bench plan produced a reproducible iCE40UP5K-SG48
configuration. It closed internal timing at 12.5 MHz and delivered `96 69`
in a functional simulation of its decoded package pins. [Local hardware inventory](host-inventory.json) · [Decision and acceptance criteria](../../docs/decisions/0053-rehearse-uart-on-fabricfox.md) · [FPGA configuration](fabricfox-v2-12p5mhz.bin)

## Timing and fit

| Seed 10, all 26 used package pins assigned | 50 MHz target | 12.5 MHz target |
| --- | --- | --- |
| Strict nextpnr exit | 1, timing failed | 0, timing passed |
| Estimated maximum internal clock | 13.540 MHz | 13.540 MHz |
| Longest register-to-register path | 73.856 ns | 73.856 ns |
| Used logic cells, embedded RAM blocks, I/O sites | 1,751/5,280, 4/30, 26/39 | 1,751/5,280, 4/30, 26/39 |

The critical path runs from program counter bit 6 to the second memory byte
lane's read-clock enable. At the passing point the released 434-clock bit cell
takes 34.720 µs, or 28,801.84 baud. The FPGA target takes an external clock.
The ASIC has its own qualified CMOS5L timing record. [50 MHz report](timing-50.json.gz) · [12.5 MHz report](timing-12.5.json.gz) · [50 MHz route log](route-50.log.gz) · [12.5 MHz route log](route-12.5.log.gz)

The package simulation has zero logic delays. Its 2 ps selector-settling
steps order digital observations. For scale, the route reports 31.135 ns
on its longest asynchronous input-to-output path and 26.583 ns from a
clocked element to an output. External arrivals and board delays were
unconstrained. A controller that budgets 32 ns for each of three serial
selector changes would need 96 ns in an 80 ns clock period. A physical
adapter must schedule the reads across available edges or establish margins
for its actual paths, then measure the combined polling and read latency.
[Routed paths](timing-12.5.json.gz) · [Host-service contract](../../docs/specs/p-uart-rx-host-service.md)

## Observations

| Check | Result |
| --- | --- |
| FPGA memory binding | The qualified SRAM model, four FPGA RAM blocks with byte forwarding, and an independent word-array oracle agreed on 16,640 clock edges. The existing 128-word program-store suite passed 2,462 checks, including two four-state checks. A one-bit bypass fault failed on edge 1. |
| Cold start and handoff | Both the successful frame case and the bad-stop case read back all 32 released program bytes. After loader edge 76, the host selected `67` and `00` with no intervening rising edge. The observed outputs were `22` and `20`. |
| Two back-to-back 8N1 frames | At exact clock ratio and the declared input phase, the host cached `96` tentatively at runtime edge 4,341. The receiver reached `A7` at edge 8,471. The host accepted `96 69` at edge 8,679. |
| Framing fault | A low first stop bit produced `E6` at edge 4,130. The host rejected at edge 4,339 and delivered no bytes. |
| Damaged image and connected peer | A changed second program byte read as `01` against expected `00` at loader edge 38. A separate run connected the idle-high modeled transmitter during that read and resolved the pads as `000000X0`. |
| Clock | An independent Verilog monitor counted all 13,246 rising edges across the four pin scenarios. The shortest period was 80,000 ps. Removing the loader's low-phase wait triggered rejection at 48,001 ps. |

The decoder initially rejected the upstream PCF option `-nowarn`. Its
initial port declarations also caused an Icarus duplicate-net error. Routing
continues to use the original PCF. The decoder now uses the same 26 named
pin assignments and its supported port-declaration mode. An early functional
pilot also allowed short loader pulses. The two committed-source runs use
the corrected driver and independently enforce the minimum period at every
rising edge. [Failure witnesses and RAM results](diagnostics.log) · [Package test receipt](package-results.xml) · [Complete observations and input hashes](result.json)

## Reproduction

The engineering window opened at 20:56:11 UTC. The first committed-source
run used `62afbccb979a992675905a37c937ab11bd7e1859` at
21:14:07–21:15:22 UTC. A fresh Git clone of the same commit ran at
21:16:17–21:17:01 UTC and passed 20 minutes 50 seconds into the 90-minute
budget. Both used read-only sources, separate H: outputs,
disabled networking and the locked image in the linked commands. The
104,090 configuration bytes, decoded Verilog digest, route reports,
input hashes and pin observations matched. The configuration SHA-256 is
`89fa89607e0eac4468d11257b4b46296f9122115e0995c888274d31387fb4163`.
The production guard passed before and after each rehearsal, and all twenty
hardware files matched both release tags. The clean repository check passed
163 unit tests. [First run](first-result.json) · [Clean run](result.json) · [Doctor](doctor.log.gz) · [Repository check](check.log.gz)

Run the experiment's PowerShell command from the repository root. To compare
its output to the archive, replace the path below with the new run directory.
Omit `--run` to check just the archived runs, timing reports and bitstream.
[Build command, models and upstream sources](../../experiments/fpga_uart/README.md)

```sh
python -B evidence/E0051-fabricfox-uart/verify.py --run build/uart-fpga-01
```

## Physical acceptance remains open

Use the named v2 breakout, a controllable external clock, a separately
isolatable UART TX, and calibrated receiver-end measurement. Keep the peer
isolated through byte readback. Capture release, both framing decisions
and host delivery. At the exact tested ratio the combined host-service
bound of 4,340 clocks is 347.2 µs. A resolved logic level alone cannot
establish release when two sources drive the same value. Fixture calibration,
oscillator accuracy, clock handoff on hardware and real host service still
need observation. [Bench acceptance criteria](../../docs/research/council-2026-11-24/next-experiments.md#3-measure-one-claimed-external-interface) · [Isolation and measurement plan](../E0049-review-council/panel-b/etr-fixture.md)
