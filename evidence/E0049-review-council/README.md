# E0049 — Multidisciplinary review of the protocol emulator

The council reviewed the published 8×4 CMOS5L design and ran bounded comparisons on copies and test fixtures. Start with the [review procedure](../../docs/research/council-2026-11-24/charter.md), [debate record](../../docs/research/council-2026-11-24/proceedings.md) and [primary sources](../../docs/research/council-2026-11-24/sources.md). The research records below give the observed results and the commands that reproduce them.

| Question | Result and reproduction |
| --- | --- |
| What was actually released? | Twenty production inputs match both tags. Fresh release metadata and the original G4 geometry agree with the audited publications. Thirteen original CI ZIPs and 3,768 member instances matched their indexes. [Release and archive checks](baseline/README.md) |
| Can the chip stay selected during loading? | With the staged loader exit on the submitted netlist, 55 G3 cases and 1,160 I²C cases match the originals. Verilator also matches G3. G4 gate simulation and Verilator each reproduce twenty applicable G5 cases. The original test-discovery error and excluded low-enable case are identified. [Gate and RTL comparisons](powered-netlist/README.md) |
| What changes on an actual carrier? | Board CAD, pin firmware and a digital enumeration identify how a readback may drive against an idle transmitter. A source-grounded interlock and calibration plan specify observations for a future instrumented test. [Hardware and electrical review](panel-b/README.md) · [Selector order and resident rearm](panel-c/README.md) |
| Can a new bus operation run in firmware? | One 85-word single-device 1-Wire power query passes the ideal-pin cases. Two 70 µs firmware profiles fail a receiver-threshold test. A 76 µs profile passes 32 modeled conditions and exposes two higher-load counterexamples. [Independent wire command](onewire/README.md) · [Sensor-end observations](onewire/rise/README.md) |
| Is a programmable alternative competitive? | A separately assembled and emulated RP2040 PIO program runs the same query. A fixed controller trades away programmability. A four-mode PIO host passes the frozen positive cases, detects the deliberate bad cases and runs eight settings consecutively. The earlier emulator stalls and input-synchronization correction are retained. [Architecture tests and replay](panel-a/replay-guide.md) · [Four-mode host comparison](panel-a/pio-spi/README.md) |
| Does the VM meet an externally timed target role? | A 59-word command/reply target recognized two opcodes and rejected 254 others, but released driven MISO 1,563 ns after a stalled-clock abort against a 160 ns target. A CS-controlled switch introduced a fresh failure at reselection. [Target, first failure and timeout sweep](panel-c/spi-target/README.md) · [Switched configurations and measurement limits](panel-b/fixture/README.md) |
| What is the price of an instruction or a smaller file? | Manual UART reproduces edge timing under its stated conditions and increases firmware size. Disabling the burst in a whole-top copy saves 2.2610% of nominal mapped cell-plus-SRAM area and breaks released burst programs. A simple dictionary shrinks six of fifteen published files; the fixed macro and existing public loader are charged separately. [Firmware and silicon cost](uart-ablation/README.md) · [Static compression and held-out images](storage-screen/README.md) |
| What would help a reader or operator? | Literal starter commands worked offline with their version-matched files. They produce a macro-port plan. An additive controller transport would need clock, direction and peer isolation operations. No operator participated. [Existing entry points and missing operations](panel-c/delivery-delta.md) · [Two-program editing trial design](panel-c/owner-comparison.md) |
| How much physical margin is established? | Both final layout archives, actual SRAM contacts, power ports and path reports were checked. Fast-corner hold reproduces at +0.120791 ns; a deliberate extra 0.125 ns uncertainty makes it negative. [Signoff extraction and limits](panel-b/signoff-rebuttal.md) |

## Replay a result

Run from the repository root in a checkout with its stored Git objects, releases and evidence. This short audit reads actual retained rows, both raw map statistics, the original program archive and Git blob bytes for the panel manifests. It also checks the local council Markdown link targets. The individual experiment guides supply the longer commands that recompile the HDL, rerun the comparisons or inspect the original GDS.

```powershell
python -B evidence/E0049-review-council/audit.py
python -B tools/production_sram.py
```

Unless a guide names a native Python run, use the project's pinned workbench on H:. Several runs also use hash-checked upstream PDK models, the pinned physical container or Raspberry Pi's assembler and the Wokwi decoder. Use fresh output names. No new physical route, fabricated device, board capture, participant test or competition submission is part of E0049. The [follow-up protocols](../../docs/research/council-2026-11-24/next-experiments.md) state which such observations could change a decision.
