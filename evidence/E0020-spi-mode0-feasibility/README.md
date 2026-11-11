# E0020 - SPI mode-0 phase feasibility and retained counterexample

Date: 2026-11-03. Base: `ae13f6bfcfd3fe21cd937768bc9e1151f441379c`.
Rungs: independent mathematics, reference execution and focused public-pin RTL.
Production RTL, official pins/config, clock target, 6x4 allocation, learning
record, compiler and visualizer source/data are unchanged. PR8 remains deferred.

**The broad mode-0 response-envelope hypothesis FAILS for the tested eight-word
schedule.** Green regressions below reproduce and retain that failure. The
mandatory P-SPI-HOST-4MODE workload remains NOT_EVALUATED. Fast-response
conditional successes and the larger model-only experiment do not qualify it.

## Formalized experiment

[Contract](../../docs/specs/p-spi-host-mode0.md),
[decision](../../docs/decisions/0021-spi-phase-feasibility-before-rtl.md).
The authoritative comparison remains 1 MHz, four modes and both bit orders.
The new oracle uses mode-0 edge conventions from
[Microchip](https://onlinedocs.microchip.com/oxy/GUID-A9964E93-D46C-42E6-98D2-4ED783ABB2CE-en-US-2/GUID-0E901CC4-8D8D-458D-8FF5-8898F0C41259.html)
and [TI SBOA621](https://www.ti.com/lit/pdf/sboa621), with explicitly chosen
digital response/setup limits. Those numbers are not universal SPI electrical
limits or claims about a commercial target.

H=25 uses 50 execution clocks per SCK period. SCK rises on accepted edges
27,77,...,377, CS asserts on 2, final fall/release is 402 and HALT is 403.
Every public output/direction is checked on every execution edge. The image is
loaded and read back through public pins; TX uses public register 1. Only the
dedicated runtime readout observes RX; no internal engine handle judges results.
All transaction clocks remain exactly 20,000 ps apart, including runtime reads.

## Falsification, not a patched success

TX=0x96, target RX=0x69, MSB first, late shift, idle MISO=1. At response d=88
quarter-clocks the raw byte is correct; d=89 crosses the synchronizer deadline.
The external target launches after the falling/setup boundary and holds the bit
across rising SCK. It remains inside this seed's declared setup envelope.

| First-bit event | Accepted-edge coordinate | Consequence |
|---|---:|---|
| Existing input sample used by late SHIFT_STEP | 24 | Old idle bit captured |
| Target's new MISO bit becomes valid | 24.25 | 445 ns after low-phase start |
| Coupled SHIFT_STEP | 26 | Sets MOSI and consumes raw edge 24 |
| SCK rising / independent target observation | 27 | Correct target bit has 55 ns setup |
| Proposed reference SAMPLE | 29 | Consumes raw edge 27 |

The real shifter captures `0xb4` at edge 376, before the final rising edge 377,
then HALTs at PC7 on 403. Independent rising-edge decoding still sees target
`0x69`. Both simulators reproduce this. LSB first produces `0xd3`. Enumerating
the entire RX alphabet at d=89 gives 255 wrong bytes out of 256 in each order;
all-ones alone masks the defect. An early-shift control fails even at d=1.
No claim that every eight-word program is impossible is made.

`python test/test_spi_mode0_oracle.py --require-mode0` deliberately exits **1**
with the retained FAIL result. This is the rejected hypothesis, not an unresolved
test-runner failure. [counterexample.json](counterexample.json) preserves it.

## Measured reference tradeoff

| Experiment | Words / used bits | Accepted edges | Final raw capture | Status |
|---|---:|---:|---:|---|
| Real late coupled image | 8 / 256 | 403 | 376 | Conditional success; declared full response envelope FAIL |
| Isolated DRIVE/SAMPLE reference | 10 / 320 | 403 | 379 | Correct at d=96 in the reference; NOT IMPLEMENTED or publicly loadable |

The split reference passes every RX byte in both orders at the latest response
(d=96), plus H=4/5 corners and order/config/reset/freeze/partial-HALT checks.
Its simple implementation declares one additional `prepared` Boolean. This is
not a physical flop count or minimum-state proof. A naive store expansion adds
64 program bits, but the actual five-bit loader byte window cannot address 40
bytes. Bank/address state and decoder costs remain unmeasured. Neither a new
memory size nor a clocked-shift architecture is selected. Run
`python test/test_spi_mode0_oracle.py --reference-cost` for the measured plan
sizes/captures and explicit NOT_EVALUATED gate/area/timing result.

The phase reference assesses its generated plan and listed guards only;
legacy/new shift interoperation and a backward-compatible encoding are also
unverified costs. It is not a replacement VM or a minimum extension claim.

## Executed checks and scope

- Existing locked image Doctor: PASS; no image build, pull or dependency install.
- Host Python 3.14.6: six focused reference tests PASS. Locked `make check`:
  PASS with 18 existing M1 +3 UART +6 SPI +4 waveform-provenance cases (31 total),
  metadata and conservative learning-status checks.
- Focused Icarus and Verilator: two groups PASS on each, with ten conditional /
  counterexample transfers, abort/reset/reload and actual rejection of a
  ten-word length. These are filtered tests, never labelled the full RTL suite.
- `node tools/export_atlas.mjs --check`: PASS; checked visualizer dataset remains
  byte-identical. No local frontend build/browser, formal, synthesis, physical,
  FPGA or silicon run was performed for this slice.
- Full-regression provenance now requires the SPI test module as well as the
  original two modules; omitting the SPI module is rejected by a fixture.
  Default full-regression dump behavior remains enabled for normal CI.

The container Doctor reports Python 3.11.16 for check commands; the retained
cocotb logs identify its embedded Python 3.11.9, cocotb 2.0.1, Icarus 14.0 devel
and Verilator 5.051. These distinct runtimes are not conflated. The image ID,
tested source hashes and focused JUnit identities are recorded in
[result.json](result.json). Fresh remote qualification belongs to the exact
published draft-PR head; local passes do not imply remote CI success.
Curated logs normalize LF and trailing whitespace only. Raw copies/hashes are
retained under ignored `build/spi-mode0-20261103/raw-logs/`; error messages and
failed outcomes are unchanged.

## Operational failures retained

1. Connected Personal Context was unavailable. The current repository, GitHub
   state, explicit delegation and older local Codex memories supplied scope;
   no unavailable context result was counted as a pass. `rg` was absent from
   this Windows PATH; scoped PowerShell reads were used without installation.
2. An ad hoc probe imported `test.test_spi_mode0_oracle` and hit host Python's
   standard-library `test` package. The direct source-file CLI above avoids that
   ambiguity; the actual expected FAIL result was then obtained.
3. The first focused Icarus run passed both groups but `FST=` only removed the
   output-format flag: the testbench still overwrote ignored `test/tb.fst` with
   a 471,830-byte focused VCD. Its copy is retained under ignored
   `build/spi-mode0-20261103/initial-focused-trace.vcd`. That trace is not usable
   as full-regression evidence; no archived evidence was modified.
4. A new `+NO_DUMP` opt-out was initially passed via SIM_ARGS, before Icarus's
   executable argument, so that invocation failed before tests. PLUSARGS fixed
   placement and passed; the final documented interface is COCOTB_PLUSARGS.
   Corrected focused runs preserve the retained trace hash. The normal CI
   regression regenerates its own correctly labelled full trace.

Reproduce focused RTL with the existing locked image, substituting simulator
`icarus` or `verilator` and a distinct output/build path:

```text
make -C test SIM=icarus COCOTB_TEST_MODULES=test_spi_mode0_public FST= COCOTB_PLUSARGS=+NO_DUMP SIM_BUILD=../build/spi-mode0-20261103/icarus COCOTB_RESULTS_FILE=../build/spi-mode0-20261103/results-icarus-isolated.xml
```

Next executable action: freeze and cost isolated phase-separated instruction
encodings against a compact eight-word alternative, including any loader
banking. Require the same response-envelope oracle before production RTL
promotion. Do not import PR8, enlarge storage or call mode 0/four-mode SPI
qualified on the strength of the conditional cases.
