# P-UART-RX-8N1 contract and semantic feasibility experiment

Status: locally verified bounded last-byte public-pin RTL experiment (E0018);
exact-head CI pending. D18 fixed delivery before the implementation measurement.

## Workload and prerequisites

Use the evaluation contract's 50 MHz target and exact period P=434, two
back-to-back 8N1 frames, all byte values, sub-clock phase offsets and bad stops.
For the reference generator only, even P in 4..32766 is legal: the bounded
start timeout 2P must fit the existing unsigned 16-bit field. Reduced P=4 is a
semantic corner, not another qualified baud rate or a physical frequency claim.

RX is `uio_in[1]`, always released (`uio_oe[1]=0`). Before execution, load/read
the eight words and write both TX payload registers (1 and 4) to `ff`. Leave
loader mode, drive RX idle high, and take two rising edges with `ena=0` to flush
loader residue from the input synchronizer. Arm PC1 before the first start;
the stimulus remains high through accepted edge 2 and first becomes low no
earlier than edge 4. An already-low partial frame is outside this workload.

Keep `ena=1` through each frame. Disabled edges freeze the engine but not the
input synchronizer and stretch elapsed time; such traces are not successful
UART reception. Reset aborts the experiment and erases program/data as already
specified. RTL reset/disable regression obligations remain required, not waived.

The mathematical stimulus uses quarter-clock ticks (5 ns at the target).
If a transition coincides with a rising edge, it is applied before that edge
in this digital oracle. Real setup/hold violations, metastability, MTBF and
clock-rate mismatch remain NOT_EVALUATED. Other phases are 5, 10 and 15 ns after
the edge. This phase coverage does not establish analog baud tolerance.

## Exact eight-word witness

| PC | Instruction | Purpose |
|---:|---|---|
| 0 | LOOP(length=6,count=2) | two frame attempts, body PC1..6 |
| 1 | WAIT_PIN(pin=1,level=0,timeout=2P,fault) | bounded start detection |
| 2 | WAIT(P/2-2) | align start-center observation |
| 3 | WAIT_PIN(pin=1,level=0,timeout=0,fault) | reject high at start center |
| 4 | WAIT(P-2) | align first data-center observation |
| 5 | SHIFT_BURST(LSB,tx=0,rx=1,period=P) | sample eight data bits |
| 6 | WAIT_PIN(pin=1,level=1,timeout=0,fault) | validate stop center |
| 7 | HALT | normal two-frame termination |

The image uses 256 program bits, the full existing eight-word store. TX pin0
is a declared dummy output: released before the first burst, driven high from
its first bit onward because both payload slots contain `ff`. It is not a
concurrent UART transmitter. No other output bit/direction changes.

Let `j=ceil(raw_start_in_clock_units)` and E=j+2. The engine consumes raw edge j
at E under the established two-stage digital model. Since WAIT execution and
the following instruction cost two edges, the explicit `-2` counts produce:

| Event | Accepted edge | P=434 offset from E |
|---|---|---:|
| Detect first start | E | 0 |
| Validate start center | E+P/2 | 217 |
| Sample data bit k, k=0..7 | E+3P/2+kP | 651+434k |
| Commit first raw byte | E+17P/2 | 3689 |
| Check first stop | E+19P/2 | 4123 |
| Detect second start | E+10P | 4340 |
| Commit second raw byte | E+37P/2 | 8029 |
| Check second stop | E+39P/2 | 8463 |
| HALT at PC7 | E+39P/2+1 | 8464 |

Raw sample time is two edges earlier than the corresponding engine edge.
Its offset from the ideal bit center is `ceil(raw_start)-raw_start`, between
zero and less than one clock. This is a derivation, not pad timing evidence.

## Capture is not acceptance; bounded last-byte delivery

SHIFT_BURST writes the generic raw RX result/valid on the eighth data bit,
before the stop check. A bad stop therefore faults at PC6 but may leave
RX-valid true with the malformed frame's byte. That flag means raw capture,
not validated UART frame acceptance. Do not hide this mismatch by relabelling
the existing register or by checking only the returned byte.

The single result register is overwritten by frame two. D18 deliberately
delivers ONLY frame two, after BOTH frames validate and the known image HALTs
at PC7. Frame one is discarded, not queued. A host accepts the final byte only
if it loaded/read back this image, performed the idle handoff, held enable high
through reception, and then observes HALT/ready/PC7 (`uo_out=a7` in status mode)
and raw-valid one. This is batch acceptance; frame one's earlier good stop is
not an independently delivered result. ANY FAULT rejects the entire batch,
even with raw-valid one and even after frame one's good stop. A stopped/disabled
or reset batch is also rejected by the host; the chip has no interruption flag.
`ui_in[7]` must also stay zero throughout reception. Any loader entry or
program/data mutation aborts the host batch, even if that loader transaction
does not drive RX. After any abort reset/reload before accepting another batch.

Use `m1-runtime-readback.md`: `ui_in=62` reads the raw byte on dedicated
`uo_out`, `63` reads raw-valid, and `00` restores status, without loader entry
or another clock. Both raw captures are inspectable on their exact eighth-bit
edge, before stop validation, but that diagnostic observation is NOT acceptance.
At HALT the second result/status is retained indefinitely, including with
`ena=0`, until reset or the existing loader data writes invalidate it. The
host reads terminal status, result and raw-valid without accepting another
execution edge. Do not re-enter the loader to read while RX is externally
driven: loader reads drive all `uio` pins and sampled entry resets execution.

No FIFO, overrun, per-frame-valid, independent service-rate or full-duplex claim
exists. The complete mandatory lossless two-byte RX delivery remains open;
this explicitly narrower batch policy must not be relabelled as that pass.

The [TI UART register reference](https://downloads.ti.com/dsps/dsps_public_sw/sdo_sb/targetcontent/tirtos/2_14_01_20/exports/tirtos_full_2_14_01_20/products/cc13xxware_2_00_03_15980/doc/register_descriptions/CPU_MMAP/UART0.html)
describes framing failure on an invalid stop and associates error information
with received data. It motivates keeping byte capture separate from acceptance;
this project does not claim to implement TI's FIFO or register interface.

## Focused falsification and next RTL obligations

`tools/uart_rx_oracle.py` generates frames and a closed-form expected schedule.
It does not execute Machine.edge. The semantic experiment separately runs the
existing model against that waveform and compares its result events, start/stop
checks, terminal edge and released RX direction.

Required meaningful scenarios:

- all 256 complementary byte pairs in the reference at exact P434, with phase corners on retained
  `00/ff` and `55/aa` patterns; no unnecessary full Cartesian phase/payload sweep;
- P4 as the smallest firmware period and rejection of a timeout-overflow period;
- absent start: FAULT at PC1 on edge 2+2P (870 at P434), no raw capture;
- RX high at sampled start center: FAULT at PC3, no raw capture; this is not
  general glitch filtering or automatic resynchronization;
- bad stop in either frame: FAULT at PC6 on that stop-center edge, despite the
  earlier raw capture; second-frame corruption must not erase that distinction.

The implementation gate is public-pin loaded dual-simulator RX traces,
including synchronizer phases, raw-result visibility, bad-start/stop status,
timeout, reset/disable and the explicit delivery policy. Independent frame
expectations must judge the RTL, not the engine model. Formal additions are
needed only for meaningful new RTL behavior. Exercise all byte values in RTL
at P4 and retain exact P434 `00/ff`, `ff/00`, `55/aa`, `aa/55` phase cases, as
in the TX split between alphabet coverage and mandatory-period corners. Verify
both raw commits before another edge, no premature acceptance, terminal final
delivery, first/second bad stops, missing first/second start, high start center,
reset/disable abort and read selection held across active edges. The RTL phase
driver orders coincident raw transitions 1 ps before the corresponding clock
edge to avoid a simulator race; this digital ordering is not pad setup evidence.
CMOS5L, gate-level and silicon remain absent.
