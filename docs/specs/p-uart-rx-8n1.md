# P-UART-RX-8N1 contract and semantic feasibility experiment

Status: proposed RTL acceptance; reference schedule checked on 2026-10-05.
This is not UART-RX RTL qualification. No production RTL changes are made.

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

## Capture is not acceptance; delivery remains open

SHIFT_BURST writes the generic raw RX result/valid on the eighth data bit,
before the stop check. A bad stop therefore faults at PC6 but may leave
RX-valid true with the malformed frame's byte. That flag means raw capture,
not validated UART frame acceptance. Do not hide this mismatch by relabelling
the existing register or by checking only the returned byte.

The existing single result register is overwritten by frame two. Capturing
both bytes in a model trace does not provide lossless end-of-program delivery.
This experiment makes no FIFO, overrun, per-frame-valid, independent host
service-rate or full-duplex claim. Public-pin intermediate readback/service or
a justified protocol-independent delivery extension must be specified and
tested before qualifying the complete mandatory RX workload.

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

- all 256 complementary byte pairs at exact P434, with phase corners on retained
  `00/ff` and `55/aa` patterns; no unnecessary full Cartesian phase/payload sweep;
- P4 as the smallest firmware period and rejection of a timeout-overflow period;
- absent start: FAULT at PC1 on edge 2+2P (870 at P434), no raw capture;
- RX high at sampled start center: FAULT at PC3, no raw capture; this is not
  general glitch filtering or automatic resynchronization;
- bad stop in either frame: FAULT at PC6 on that stop-center edge, despite the
  earlier raw capture; second-frame corruption must not erase that distinction.

The next implementation gate is public-pin loaded dual-simulator RX traces,
including synchronizer phases, raw-result visibility, bad-start/stop status,
timeout, reset/disable and the explicit delivery policy. Independent frame
expectations must judge the RTL, not the engine model. Formal additions are
needed only for meaningful new RTL behavior; no new hardware proof is claimed
by this reference-only experiment. CMOS5L, gate-level and silicon remain absent.
