# G2 preparation - I2C controller acceptance draft

Status: **DRAFT, NOT IMPLEMENTED OR QUALIFIED**, 2026-11-12.
Prepared while G1's physical jobs run. G1 remains the active goal.
Freeze this contract and an independently tested oracle before changing the ISA.

## First workload

Use one controller and a scripted target on the existing public pins.
The first gate proposes three finite transactions: one-byte write, one-byte
read, and one-byte write followed by repeated START and one-byte read.
Include address/data ACK and NACK outcomes. Multi-byte receive and
multi-controller arbitration require separately stated delivery/ownership rules;
they are not implied by this first gate.

Load and read back every program through the real loader. Change address,
payload and transaction kind through documented program/data inputs, without
recompiling RTL. Compare UART, SPI and I2C at one candidate revision before
production promotion.

## External digital interface

Proposed mapping: uio0 = SCL, uio1 = SDA. During bus execution, a driven line
must have output value zero; output enable selects pull-low versus release.
Resolve the controller and target contributions into one wire value and feed
that value back through uio_in. The oracle must inspect both output value and
direction: a push-pull high is a failure even when the resolved bit looks right.

The target's stimulus depends on decoded bus events, never the executor's
private state. Timestamp raw bus transitions independently of the program
model. Use the existing two-register input path, with its documented latency;
do not substitute an ideal raw-pin read inside the executor.

The loader currently shares and can actively drive all uio pins.
The test must isolate the protocol target during loading, then connect the
idle bus and perform the documented two-edge input flush before execution.
This is an explicit host/board requirement. Runtime result reads use dedicated
uo_out and must not pause clk or change bus ownership.

## Timing authority and project choices

[NXP UM10204 Rev. 7.0](https://www.nxp.com/docs/en/user-guide/UM10204.pdf),
sections 3.1 and 6.1/Table 11, remains authority S13. Checked 2026-11-12.

For the Standard-mode digital screen, enforce these minima on resolved wires:

| Measurement | Minimum | Ceiling at 20 ns |
|---|---:|---:|
| SCL low | 4.7 us | 235 clocks |
| SCL high | 4.0 us | 200 clocks |
| Data setup | 250 ns | 13 clocks |
| Repeated START setup | 4.7 us | 235 clocks |
| START hold | 4.0 us | 200 clocks |
| STOP setup | 4.0 us | 200 clocks |
| Bus free | 4.7 us | 235 clocks |

Clock frequency must not exceed 100 kHz. START/STOP, byte ordering,
acknowledgement and stretch handling are checked against the referenced
protocol, independently of decoded instructions. A target holding SCL low
must postpone the next high phase until the resolved wire rises.

Project reference waveforms will use 260 low clocks and 240 high clocks when
unstretched: 500 clocks per bit at the 50 MHz target. Execution overhead must
be measured; a slower passing transfer is reported with its actual rate.
Ideal pull-ups and discrete levels establish no pad, RC, voltage, noise,
metastability or electrical-compliance result.

Proposed bounded policy: each released-SCL wait has a 50,000-clock deadline
(1 ms), including input-observation latency. On expiry, produce a distinct
public failure outcome and release both lines within another 16 clocks.
The precise public status encoding and final-observation-edge priority must
be frozen with a program schedule before testing. This timeout is our project
policy, not a claim that I2C imposes a 1 ms limit. Do not label a forced release
while SCL remains low as a successful STOP.

## Independent oracle and falsification plan

Before RTL experiments, generate reviewed reference traces and mutation controls.
The oracle takes public wire/drive events and declared transaction expectations;
it must not import the ISA interpreter, compiler or generated expected pin trace.

Required controls include active-high drive, SDA changing during an ordinary
high phase, a short low/high/setup interval, swapped data bits, missing or extra
ACK clock, continued data after a rejecting ACK, wrong final response, repeated
START replaced by STOP, advancement during a held-low SCL, premature timeout,
and a stale RX value falsely presented as a fresh transaction result.

Exercise all 256 single-byte data values with retained deterministic seeds.
Place stretch intervals at address, data and ACK boundaries, including
release on either side of the declared deadline and a permanently held line.
Check both phase offsets and discrete input-delay limits explicitly.
Reset, disable and loader entry during a transaction must be recorded as
abort/control cases, not accepted protocol transactions.

Each proposed case needs a finite completion bound, public outcome and exact
coverage count before the first candidate run. Pass the same oracle on both
RTL simulators, retain counterexamples, then add relevant formal properties.
Program capacity and real storage cost remain measurements.

## Existing-machine obstacle to test first

SET can express pull-low/release with value zero and varying output enable.
The current SHIFT_STEP and experimental DRIVE paths instead drive payload bits
with TX output enable asserted; ordinary one bits therefore do not implement
this draft's open-drain rule. See [K-SHIFT-8](k-shift-8.md) and
experiments/spi_phase/build_variants.py.

First try a public-loaded SET/WAIT/WAIT_PIN baseline and measure its complete
transaction footprint. This identifies whether the first limitation is
capacity, data-dependent output enable, receive sequencing or timeout cleanup.
Only then evaluate a general instruction change or a larger store, using G1's
physical measurements. Do not assume eight words is a final memory limit, or
add dedicated I2C RTL merely to make the workload pass.
