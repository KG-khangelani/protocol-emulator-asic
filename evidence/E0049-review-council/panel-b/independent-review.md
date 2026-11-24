# Hardware, electrical and embedded review

Prepared independently on 24 November 2026. The review concerns the D48
production core, 0x22, G4 physical source `45c55f7` and G5 software examples.
Source documents below were accessed on 24 November. Estimates of future
effort are engineering planning ranges.

## Hardware implementation and verification

**Retained qualification.** Two separately dispatched builds from the same
physical inputs produced the same submitted netlist, matching geometry apart
from GDS timestamps, ten passing prechecks and eighteen passing public
zero-delay gate-level groups each. The independent wire expectations, injected
errors and archived failures make this much stronger than counting passing
workflow badges. The UART groups executed assertions, while the retained
comparison covers 97 RX/late-reader landmarks. It does not contain complete
paired UART TX waveforms. Earlier global-routing congestion, nine extracted
SRAM input-slew violations, incompatible power ports and contact-rule findings
explain the risk of changing a passing physical baseline. See the E0036–E0045
decisions and the E0047 reproduction record.

**Fresh inspection of retained reports.** The panel verified the complete GDS
log and gate-test archive hashes for both G4 runs and the member hashes for
the individual reports it read. The slow setup path starts at SRAM
`A_DOUT[24]` and ends at flop `_7498_`, with 5.595886 ns slack. The fast hold
path starts at flop `_7350_` and ends at SRAM `A_ADDR[6]`, with 0.120791 ns.
For that hold path the reports give arrival 1.069597 ns and required time
0.948806 ns. The fast standard-cell library is −40 °C and the SRAM library is
−55 °C. This particular mixed-temperature interface lies on the worst hold
path. The slow corner is 1.08 V, 125 °C for both. The 20 ns final SDC specifies
0.25 ns clock uncertainty and 4 ns external I/O delays. These are inputs to
tile timing analysis. They cannot characterize a peripheral, the bus, the
package or an asynchronous input's mean time between synchronizer failures.
[IHP's preview status and process description](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/e73adb4045731ddec21634146d536380057f6a26/README.md)

**Position.** Retain the routed candidate and its mixed-corner disclosure.
If the foundry or final shuttle supplies a consistent-temperature macro model
or changes the PDK, replay both paths with every declared gate and the original
comparison. Clock-period relaxation addresses setup differently from hold and
cannot be assumed to cure a same-edge hold failure. Missing silicon, library
data or a board does not reopen a completed competition flow gate. Jane
Street's published signoff requirement is the Tiny Tapeout flow and precheck.
[Competition FAQ](https://blog.janestreet.com/protocol-emulator-asic-competition/)

**Objection to my position.** Preserving this core says little about global
minimality. The route contains 4,679 standard cells and 61,294.1 µm² of
standard-cell area. The physical 256×32 macro and fixed 8×4 footprint are
additional facts. The 128 logical words use half of the physical bit capacity.
Using the rest for a receive FIFO would compete with next-PC fetches on a
single synchronous port. Count buffering, arbitration and lost or delayed
pin edges before claiming that another 4,096 bits of buffering are free. Only
a matched complete-chip implementation could establish its physical cost.

## Electrical engineering

**Trace observation.** Both official gate archives contain the same accepted
`output/i2c/write_read-96.json`. Its fastest clock is 98,619.329 Hz under
ideal pull-ups. At trace ticks 5,824 and 5,828 the controller pulls SCL then
SDA low. At 5 ns per tick the command separation is 20 ns. The target leaves
SDA released at that transition. UM10204 Table 11 note 2 requires SCL to
fall below 0.3 VDD before SDA leaves the high region. Positive command
ordering alone cannot supply that threshold ordering.
[NXP UM10204 Rev. 7.0, Table 11 and Figure 38](https://www.nxp.com/docs/en/user-guide/UM10204.pdf#page=44)

**Conditional calculation.** For exponential falls from VDD, let `f` be
the 70%-to-30% fall time of each line. SCL reaches 30% after
`1.42096 f_SCL` and SDA reaches 70% after `20 ns + 0.42096 f_SDA`.
The ordering margin is SDA's crossing time less SCL's crossing time.
A hypothetical 10/10 ns pair gives +10 ns, 20/20 gives zero, and 100/20
gives −113.68 ns. All three use individual bus fall times below 300 ns.
This is a conditional counterexample to inferring electrical compatibility
from a passing digital trace. Actual pad waveforms could differ in either
direction, and this one transition contains no later closed-loop effects.

**Magnitude of a separate rise constraint.** At a hypothetical 4.7 kΩ and
100 pF, a first-order pull-up gives a 30–70% rise of 398 ns. At 400 pF it
gives 1,593 ns against the 1,000 ns Standard-mode maximum. At 3.3 V and a
hypothetical 0.4 V/3 mA guaranteed sink, the static minimum pull-up is
967 Ω. These examples require fixture-specific capacitance, voltage and
weakest sink capability before they can select a real resistor.
[NXP UM10204 §7.1](https://www.nxp.com/docs/en/user-guide/UM10204.pdf#page=50)
[TI SLVA689A §2](https://www.ti.com/lit/an/slva689a/slva689a.pdf)

**Position and limit.** Measure real threshold order on a declared fixture or
build a closed-loop digital model with independent crossing delays. Compare
the published program with a firmware copy adding a short interval before
changing driven SDA. Test ordinary bits, ACKs and repeated START separately.
Hardware-independent delay replay is a screen for the sensitivity of a
declared load. Fixed offline shifting of entire traces would ignore the core
waiting for synchronized SCL high. A project that has only simulation can
supply a conditional envelope and leave board measurements open.

## Embedded systems

**Integration finding.** The versioned generated plans sample reset, identify,
all program readbacks, register reads and two idle-flush edges with `ena=0`.
The fifteen G3/G5 examples use 39–391 such edges each. Jane Street says board
deselection removes power. In an actual earlier IHP CMOS5L shuttle the same
selection gates the user input bundle, user enable and power enable. The bundle
includes clock. Thus deselecting an ordinary mux user cannot supply the
disabled clock edges prescribed by the logical project-port plan. The final
March 2027 wrapper is a dependency for a shuttle-specific claim. The published
tests exercise the documented project ports and remain valid on that boundary.
[Sponsor's reset and host FAQ](https://blog.janestreet.com/protocol-emulator-asic-competition/)
[IHP 0p4 shuttle source at dae4c4e](https://github.com/TinyTapeout/tinytapeout-ihp-0p4/tree/dae4c4eaf3a404a4ba5ecf4cd8b65d01e85294a2)
[Selection and gated input RTL](https://github.com/TinyTapeout/tt-multiplexer/blob/3e496494ee9f543ec4b84e5e71bdaee25e958ce1/rtl/tt_mux.v#L289-L319)
[Project clock and user enable wiring](https://github.com/TinyTapeout/tt-multiplexer/blob/3e496494ee9f543ec4b84e5e71bdaee25e958ce1/rtl/tt_user_module.v.mak#L45-L79)

**Fresh public-pin experiment.** Two DUTs used the unchanged production RTL
and the hash-bound vendor SRAM. The first ran the existing plans. The second
kept `ena=1` on every clock. For two idle edges it selected ignored loader
write `E7`, with released pins and the attached environment idle. With the
clock low the host dropped only the load bit to `67`, then selected status
`00`. On all 15 example images the proposed procedure met all 2,890 public
loading steps and matched the reference's first 64 execution edges per image
at static idle. A synthetic word-zero WAIT_PIN must see a high input before a
literal SET and HALT. Those outcomes passed. Only one correct warm-up level
gave FAULT at PC zero, a bank-select write invalidated ready, and a deliberately
interposed A7 read drove all eight pins even while the clock was stopped.
The first fixture failed on reset initialization at simulation time zero.
Applying reset after simulation started fixed the fixture. Both original
result files are retained.

**Objection to my proposed procedure.** Two copies of the same RTL and one
simulator can agree on the same defect. The separate literal witness and
negative controls answer narrower questions. This was a prefix at settled
levels, without complete peer-driven UART/SPI/I²C transactions, pad timing,
board firmware or a model of the actual March shuttle. Deliberately split
enable/driver transitions in a real host need to cover *every* read/write
turnaround. A direct change of E7 to 00 can transiently enter loader read
if write falls before load.

**UART and SPI.** Host-serviced UART RX must quarantine the first byte and
discard both on framing error. At period 434, the safe copy condition is
`H + L ≤ 4,340` 20 ns edges, or 86.8 µs. The published oracle may use three
combinational selector reads in one edge. An RP2350 SDK call or a USB-attached
host has no measured worst-case latency here. Use deterministic hardware I/O
or DMA ahead of unrestricted host software if claiming lossless service.
The held-response SPI program consumes MISO sampled 22 core clocks (440 ns)
after the nominal sample edge at its 1 MHz setting. A historical exact-sample
schedule occupies one extra word, now affordable. It changes the allowed
target response envelope. Test earliest and latest values and hold the
observed SCK/CS/MOSI trace constant before recommending it for a named target.
[Microchip SAM C20/C21 §32.6.2.5](https://onlinedocs.microchip.com/oxy/GUID-DDF2C9BC-07FB-4ABF-938A-774B157B4519-en-US-11/GUID-0E901CC4-8D8D-458D-8FF5-8898F0C41259.html)

## Proposed experiments and debate questions

| Order | Hypothesis and cost | Required evidence and stopping rule |
|---|---|---|
| 1 | A selected-only host can run complete published workloads. Allow 1–2 engineer-days, existing digital infrastructure and zero hardware change. | Bind actual available mux behavior, use separate chip/host/target drive enables, execute real loader readbacks and full independent G3/G5 oracles in both simulators. Declare port-only pause controls separately. Force incorrect turnaround, one-edge warm-up, bad byte and power-cycle/reload. Reject a stored-byte, drive, execution or outcome mismatch, and retain the witness. |
| 2 | A firmware guard admits the declared I²C load envelope. Allow 1–2 days for feedback-based screening and 0.5–1 lab day if a fixture exists. | Freeze R/C, pad propagation, source/sink slew and peer timing ranges. Capture 0.3/0.7 VDD crossings, data valid/ACK, high/low periods, ordinary/repeated START, STOP, NACK and stretch deadlines. Require all minima/maxima across the frozen cases with one deliberately early SDA control. Report worst margin and actual clock rate. A failure or missing fixture limits the resulting claim. |
| 3 | The existing UART host can meet its discrete service budget. Allow 1–2 embedded engineer-days with a timed surrogate GPIO peer and logic analyzer if available. | Define end-to-end H/L including selector settling, test all poll phases analytically and exercise last-safe and first-unsafe schedules with distinct bytes and malformed stops. Require computed worst-case latency including jitter ≤86.8 µs at P434, valid framing and atomic commit. Report measured stresses separately from a proven latency bound. |
| 4 | An early SPI sample is valuable for a named peer. Allow 0.5–1 day. | Use the historical exact family, one extra word and no new opcode. All eight mode/order programs must produce the expected byte and canonical outward edges under the declared input aperture. Keep late-response and held-only controls. Defer if no intended peer or workload benefits. |

The hardware seat asks how a proposed store or queue will preserve next-PC
fetch on *every* timed edge and which complete-chip baseline includes the
loader and external buffering. The electrical seat asks which actual fixture
supports a line threshold and how failures will change the supported load.
The embedded seat asks whether a proposed demo can execute the loader from
pad-accessible operations and detect stale or malformed results. A reserve
question is whether one resident image can run repeated transactions with
only payload writes and a safe re-arm. The 96-word combined I²C example's
full plan takes 802 clock edges. At a hypothetical 1 MHz loader this is
802 µs, compared with 402.92 µs from judged idle to HALT in one retained
accepted 50 MHz target trace. End-to-end performance depends on reload policy.

## Reproduction and provenance

Run `python -B inspect_retained.py` from the repository root with the script's
path, or set the working directory to the root before invoking it. It streams
the committed G4 ZIPs and prints JSON. For the launch test, put
`run_launch.py` and `launch_tb.sv` together. In the locked workbench with
the checkout mounted read-only and a fresh writable directory, run
`python3 <script>/run_launch.py --root <checkout> --out <new-directory>`.
The host's `make` executable was unavailable. The first restricted Docker mounts
put the artifact root outside build and then made the Icarus temporary path
read-only. With the panel's H: directory bound below the checkout's build
path and its scratch temp bound at /tmp, `make doctor` passed. Icarus and vvp
reported 14.0 development build `s20260301-328-geda9fdcd1-dirty`. Image
identity was `sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909`.

The local primary records are `src/project.v`, `src/m1_data_store.v`,
`src/m1_input_sync.v`, `src/m1_program_store.v`, `tools/assembler.py`,
`docs/isa.md`, `docs/specs/p-uart-rx-host-service.md`,
`docs/specs/p-spi-host-4mode.md`, `docs/specs/p-i2c-controller-100k.md`,
`evidence/E0027-four-mode-schedule-screen/` and
`evidence/E0047-g4-submission-candidate/ci-43543626249/` and
`ci-43543629839/`. Each source was inspected for this review.
