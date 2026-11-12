# G2 I2C controller acceptance contract

Status: **acceptance frozen before ISA extension**, 2026-11-12, D36/E0032.
The independent digital oracle is tested; no I2C RTL or physical qualification
is claimed. D35's qualified compact10 pilot, with ten program words and its
real banked loader, remains the integration baseline.

## Workload and boundary

One controller and a scripted target perform three finite transactions:
one-byte write, one-byte read, and one-byte write followed by repeated START
and one-byte read. Ordinary seven-bit addresses are 0x08..0x77; reserved
addresses, ten-bit addressing, multiple controllers, arbitration, multi-byte
receive and bus recovery require separate contracts. Transmit each byte MSB
first, with a ninth ACK/NACK clock. Check address and write-data ACK/NACK;
the controller ends its single received byte with NACK, then STOP. A rejected
address/data byte takes the bounded STOP/NACK outcome without continuing data.

Load and read back every program through the public loader. Address, payload
and transaction kind vary through program/data inputs without recompiling RTL.
UART, all four SPI modes in both orders and I2C must pass at one candidate
revision before production promotion.

## External digital interface

uio0 is SCL; uio1 is SDA. During bus execution a driven bus line has output
value zero. Output enable selects pull-low versus release. Resolve controller
and target contributions with ideal pull-ups and feed the resolved bus to
uio_in. Inspect output value AND direction: active-high drive fails even if
the wire value is otherwise correct. Only the controller initiates falling
SCL edges; the target can prolong an already-low phase. The transmitter
releases SDA for the ninth clock; the receiver pulls it low for ACK or releases
it for NACK. Check ownership throughout each high phase as well as wire bits.

The RTL target stimulus must depend on decoded public bus events, never the
executor's private state. Record every public drive, direction, wire, result
and state transition, including target changes between core edges. The oracle
imports no ISA interpreter, compiler, program generator or waveform reference.
Its procedural fixtures are independent waveforms, not chip results.

Retain the existing two-register input path. For a raw input transition
strictly after core edge B, the executor first consumes that value on B+3.
Use a 5 ns event grid and a 20 ns core period. An event at tick t is after its
grid edge; its first consumable core edge is `4*(floor(t/4)+3)`. This is a
discrete synchronizer transport model, not a metastability/MTBF guarantee.

The loader shares and can actively drive all uio pins. The host must isolate
the target before entering loader ownership, reconnect an idle bus after
loading, and give the synchronizer two disabled flush edges. Mark the beginning
of the judged trace after the program has established released SCL/SDA and
zero outcome markers; include a complete idle interval before START. Trace
adapters must separately check initialization never drives a bus line high.
Read results using the dedicated uo_out runtime selectors with clk running;
decode execution state using the normal public status selector. No internal
DUT handles substitute for public observations.

## Timing authority and project choices

[NXP UM10204 Rev. 7.0](https://www.nxp.com/docs/en/user-guide/UM10204.pdf),
sections 3.1 and 6.1/Table 11, remains authority S13; checked 2026-11-12.

| Resolved-wire measurement | Limit | 5 ns ticks |
|---|---:|---:|
| SCL low | at least 4.7 us | 940 |
| SCL high | at least 4.0 us | 800 |
| Data setup | at least 250 ns | 50 |
| Repeated START setup | at least 4.7 us | 940 |
| START hold | at least 4.0 us | 800 |
| STOP setup | at least 4.0 us | 800 |
| Bus free before START and before accepted terminal result | at least 4.7 us | 940 |
| Complete clock cycle | at least 10 us | 2000 |
| Data/ACK valid delay after falling SCL, when low is not stretched | at most 3.45 us | 690 |

For stretched low phases, retain the data setup limit before resolved SCL
rises. Apply the maximum valid-delay exception only to a visibly stretched
phase. The digital screen requires SDA changes strictly after falling SCL,
not simultaneous with it. This extra ordering rule is a project margin for
Table 11's threshold-ordering requirement; it does not prove analog hold time.

Reference unstretched pulses use 260 low clocks and 240 high clocks: 500 core
clocks per bit, exactly 100 kHz at the 50 MHz target. Measure actual candidate
overhead and rate; a slower pass must be labelled with its actual rate. Check
both full low/high cycles and consecutive sampling-edge spacing. Ideal pull-ups
and discrete levels establish no pad, rise/fall, RC, voltage, capacitance,
noise, spike-filter or electrical-compliance result.

## Public result and bounded waiting policy

Firmware uses ordinary GPIO uio[4:2], with output enables asserted, for a
three-bit result marker. uio[7:5] remain released. These markers allocate no
protocol-specific hardware state.

| Marker | Meaning | Acceptance condition |
|---:|---|---|
| 0 | Running/uncommitted | No received byte accepted |
| 1 | OK | Complete expected transaction, STOP, bus-free interval, HALT |
| 2 | NACK | Rejection at declared address/data boundary, STOP, bus-free interval, HALT |
| 3 | TIMEOUT | Expired SCL observation deadline, both lines released, HALT |

Markers become meaningful only with HALT and the complete checked trace.
FAULT is not an accepted cleanup outcome. For a successful read, raw RX/valid
must expose the declared target byte at terminal HALT. The host invalidates
raw-valid through the existing payload-load operation before each transaction.
Intermediate address/partial/old raw results are not accepted I2C data. Test a
distinct stale byte; identical old/new values cannot alone establish internal
capture provenance, which also needs relevant RTL/formal checks.

Every controller SCL release at core edge R has deadline D = R + 50,000 core
clocks, including input observation latency. A high observed on D wins; one
first observable after D loses. The controller keeps SCL released and SDA
unchanged until the observation or expiry. On timeout it sets TIMEOUT,
releases both lines and reaches HALT no earlier than D and no later than
D+16 clocks. A forced release while the target holds SCL low is cleanup, not
a successful STOP. This 1 ms wait limit is project policy, not an I2C limit.

For post-edge events on the 5 ns grid, raw high at D-13 ticks is seen on D-4;
D-9 is seen on D and wins; D-8 is first seen on D+4 and loses. Exercise all
three and a permanently held SCL at every clock release, including ACK,
repeated START preparation and STOP preparation. A write/read has 19 releases;
write/read combined has 38. Rejected shorter transfers have correspondingly
fewer clocks. The whole finite trace must end within 100,000 ticks plus
200,000 ticks per expected release plus 64 cleanup ticks. This generous
completion ceiling is not a throughput claim.

Reset, disable and loader entry are explicitly declared abort/control cases,
never accepted protocol transactions. Reset clears GPIO and raw result/valid;
disable freezes architectural output/result/state and does not promise bus
release. Loader entry requires target isolation before loader ownership.
The abort checker checks the completed pre-intervention bus prefix and the
declared held control's effects; a fresh resume/reload needs a separately judged
transaction. Normal transfer/timeout bounds assume reset deasserted, ena=1,
load=0 throughout. A truncated trace without declared intervention fails.

## Independent oracle and required controls

`tools/i2c_oracle.py` consumes complete public event records and transaction
intent. The procedural `tools/i2c_reference.py` supplies reference fixtures;
hand-calculated wire bits/timestamps test it separately. Qualification is
reproducible with `python3 experiments/i2c/qualify_oracle.py`; the unit suite is
also part of `make check`. E0032 retains source/trace hashes, inputs, seed,
results and counterexamples.

Exercise all 256 byte values for every transaction kind, all ordinary addresses,
all four target-event phases, the data-valid/setup boundaries, each allowed
NACK and every SCL release with stretching and deadline-adjacent responses.
Negative controls cover active-high drive by either actor, incorrect wired-AND
resolution, target-generated clocks, high-phase SDA/ownership changes, short
timing intervals, late valid data, swapped/wrong bits, wrong address, missing
or extra ACK clock, continuation after NACK, wrong final response, STOP in
place of repeated START, direction advancement while SCL is held low,
premature/late timeout, failed release, stale RX and absent terminal status.

Pass the same oracle on both RTL simulators, with real public loading/readback,
then relevant formal properties and fresh pinned physical qualification. The
fixture qualification itself satisfies none of those hardware gates.

## Existing-machine baseline before ISA changes

SET can express pull-low/release using value zero and varying output enable.
Current SHIFT_STEP and experimental DRIVE instead actively drive payload ones;
they cannot directly implement this open-drain rule. See
[K-SHIFT-8](k-shift-8.md) and experiments/spi_phase/build_variants.py.

Measure a public-loaded SET/WAIT/WAIT_PIN baseline and its complete transaction
footprint. Identify capacity, data-dependent direction, receive sequencing and
timeout-cleanup limits before choosing a general instruction or larger store.
WAIT_PIN's current FAULT holds GPIO; timeout skip inside a LOOP is not a cleanup
escape. Preserve such failures. Do not claim an abstract oversized image was
publicly loaded, infer a global ISA minimum from one schedule, assume eight or
ten words is a final limit, or add dedicated I2C RTL to hide a flexibility failure.
