# E0052 — Physical UART reception on two public FabricFox boards

On 24 November 2026 a Docker client loaded the existing E0051 bitstream onto
two real iCE40UP5K FPGAs in the Welland public lab. On each board the RP2350
read back the released 32-byte receiver over the physical pins and sent two
back-to-back 8N1 frames. Both FPGAs delivered `96 69`, then `3C A5` in a
separate trial. Both rejected first- and second-stop faults. The largest
observed host-service bound at 12.5 MHz was **109 µs** against **347.2 µs**
allowed. The weak-bias test could not distinguish a released UIO1 from a
driven high. [Board 1 raw terminal](board-1/terminal.log) · [Board 4 raw terminal](board-4/terminal.log) · [Physical acceptance criteria](../../docs/decisions/0054-run-uart-on-public-fabricfox.md)

## Physical results

| Trial | Delivery on both boards | Board 1 service upper bound | Board 4 service upper bound |
| --- | --- | ---: | ---: |
| 1 MHz, `96 69` | Both bytes after `A7` | 108 µs | 108 µs |
| 12.5 MHz, `96 69` | Both bytes after `A7` | 109 µs | 106 µs |
| 12.5 MHz, bad first stop | `E6`, no delivered bytes | 72 µs | 69 µs |
| 12.5 MHz, bad second stop | `E6`, tentative `96` discarded | 66 µs | 71 µs |
| 12.5 MHz, `3C A5` | Both changed bytes after `A7` | 107 µs | 108 µs |
| 12.5 MHz, fresh load of `96 69` | Both bytes after `A7` | 106 µs | 105 µs |

Each successful load used 76 physical clock pulses, checked the eight-word
length and both `FF` payload registers, then observed identity `22` followed
by ready status `20` with the clock parked. A corrupted second program byte
read as `01` instead of `00` on edge 38 of each board's negative control.
The six subsequent loads on each board read back the complete original image.
[Board 1 receipt](board-1/result.json) · [Board 4 receipt](board-4/result.json)

The RP2350 and FPGA are separate chips on the demo board. The RP2350's PIO
drove the project clock and the RX pad over PCB traces. A second PIO machine
counted 100,000 periods on the clock pad. The controller timed those counts
at 8,012–8,024 µs for the 12.5 MHz runs, including software observation
overhead, against 8,000 µs nominal. At 1 MHz the readings were 100,016 and
100,021 µs. The generated UART uses exactly 434 clocks per bit, about
28,802 baud at the higher rate. Clock and transmitter share the RP2350
oscillator. The records cover this phase, rate relationship and finite set
of trials. Absolute oscillator accuracy and interoperability with an independent
transmitter need their own measurements. [Clock and peer implementation](../../experiments/remote_uart/on_board.py)

## What changed after the first physical run

The first MicroPython controller already received `96 69` on physical pins.
At 12.5 MHz it took up to 317 µs between poll starts and 299 µs to complete
a read sequence. Adding 2 µs for timer quantization gave **618 µs**, which
failed the bound. A native GPIO register reader on its own reduced the
largest target-rate observation to 347 µs. Compiling the polling loop as
well gave the results above. Every version used the same FPGA image and
program. The final selector read waits four transitions of the one-microsecond
timer, giving at least 3 µs of settling. The bound sums the largest observed
poll gap and read duration, even when they occurred on different polls.
[First failure](first-host/terminal.log) · [Register-reader pilot](register-reader-pilot/result.json) · [Pilot board-side patch against 2d2d178](register-reader-pilot/board-reader.patch.gz)

## Remaining electrical question

With the RP2350 data driver disabled, the test applied its weak pull-down,
sampled UIO1 after 250 µs, then applied its weak pull-up and sampled again.
The FPGA's known low read `0,0` and its known high read `1,1`. The requested
release also read `1,1` in all twelve full loads. This setup therefore gives
no release-time or high-impedance verdict. It did establish program readback,
physical frame reception, framing rejection and timed host delivery. The
next bench measurement needs a characterized bias and target-branch current
or differential-voltage capture with known high, low and released controls.
[Fixture and calibration design](../E0049-review-council/panel-b/fixture/bench.md) · [Electrical acceptance](../../docs/research/council-2026-11-24/next-experiments.md#3-measure-one-claimed-external-interface)

## Reproduce or build the fixture

The public lab exposes the board list, a bitstream-upload form and the
MicroPython serial terminal. Its demo harness has the same 26 active package
pin assignments as the E0051 image. Both boards were present with zero
connected clients when selected. Their public device identifiers have
different SHA-256 fingerprints in the receipts. Both restored the RP2350
system frequency to 133 MHz and ended with all eight controller data
drivers released. The public image remains available in the provider's
volatile gallery. [Lab boards](https://tinytapeout.fpgas.online/) · [User upload guide](https://docs.fpgas.online/en/latest/user/boards/tt-fpga/own-bitstream.html) · [Provider's pin map](https://github.com/fpgas-online/tinytapeout-fpga-demos/blob/da7d10db1ff62b0a346381530c7c59505ea6b2ad/harness/tt_fpga_fabricfox.pcf)

Tiny Tapeout publishes the v2 FPGA breakout schematic, bill of materials,
Gerbers and component placement files. These provide a buildable starting
point for a private instrumented fixture. The carrier, controllable peer
and calibrated probes are also needed to reproduce the electrical test.
[FabricFox v2 fabrication files](https://github.com/TinyTapeout/pcb-files/tree/4d6aa7d91db2b9f4f0ac8b83af80e99ee1a25cc9/ETR/fabricfoxFPGAv2p0) · [Breakout and carrier guide](https://tinytapeout.com/guides/fpga-breakout/)

The experiment started at 21:35:14 UTC. Board 1 ran from 21:52:32 to
21:52:57 UTC. Board 4 ran from 21:53:49 to 21:54:16 UTC from a fresh
sparse checkout of the same committed source, `3959d6a`. Its initial
checkout omitted a historical Python import and failed locally before
contacting the board. Adding that tracked directory allowed the documented
client to run. Both executions used the locked Docker image with read-only
sources and H: output. The software-only FPGA test also rebuilt with
networking disabled and matched the original configuration, decoded logic,
route reports and digital observations. [Remote Docker command](../../experiments/remote_uart/README.md) · [Offline Docker command](../../experiments/fpga_uart/README.md) · [Offline replay](offline-result.json)

The repository checks passed all 163 unit tests. All twenty qualified
physical inputs matched both release tags. The offline evidence checker
also rejected a swapped delivered pair and a reconstructed 410 µs service
bound. Fabricated-silicon and calibrated analog measurements remain open.
[Workbench inventory](doctor.log.gz) · [Repository check](check.log.gz)

From a repository checkout, the following command verifies the archived
raw terminal bytes, code identities, physical observations, clock counts
and comparison to E0051. It needs Python and Git and runs without a board
or a network.

```sh
python -B evidence/E0052-remote-uart/audit.py
```
