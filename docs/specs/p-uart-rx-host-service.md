# Bounded two-byte UART-RX host service

Status: qualified bounded digital contract at `9379d68`, D19/E0019.
Existing chip/firmware unchanged; final-record CI/integration tracked at PR8.
This extends E0018's last-byte policy only for an explicitly serviced batch.
Qualification records are in E0019; a proof of integer service arithmetic
is not a proof of physical host timing.

## Workload and ownership

Use the exact eight-word image, two back-to-back 8N1 frames, P434 mandatory
point and even reference periods P4..32766 from `p-uart-rx-8n1.md`. The external
source and chip clocks have the declared exact ratio; analog baud mismatch,
metastability and physical read access time remain NOT_EVALUATED.
Public RTL qualification covers P434/P4; maximum legal P32766 is checked
algebraically, not claimed as enumerated RTL protocol coverage. Load/read
the image and write both TX slots ff with the UART source quiesced. Exit loader,
flush idle high on two disabled edges, confirm raw-valid zero, then arm.

During reception/reset-free terminal service hold ena=1, rst_n=1, ui7=0. Never
pause execution, enter loader, mutate data/program, or drive the released RX1.
The source owns RX1; dummy TX0 is chip-owned as before. The host owns dedicated
ui controls and samples dedicated uo. Abort on any observed control interruption
or service deadline miss; discard tentative data and reset/reload. No hardware
interruption/overrun detector is claimed. After acceptance, disable is allowed
as in E0018 terminal retention. This is not an unbounded or continuous receiver.

## Observations and read schedule

Number execution edges from one. All host samples occur after an edge's register
update and combinational settling; this is a clock-synchronous digital host,
not an asynchronously scheduled OS driver. Poll every H integer edges, starting
at first_poll in 1..H. At each poll read raw-valid with ui=63 (hex) and status
with ui=00, allowing settling between selections. Confirm program-ready and
reject FAULT. Neither read enters loader or changes GPIO/engine.

The first poll with raw-valid=1 schedules a raw byte read (ui=62) exactly L
integer edges later, L>=1. Cache this byte ONLY as tentative byte one. Polling
continues; poll and byte reads coinciding on one edge may share a settled
status/valid observation. The host must budget all selector-settle/sample
operations inside its service period; no pad access time is established here.
One edge needs at most status/valid/byte selections; clocks must not stretch.

Only known-image HALT/ready/PC7 (a7) with raw-valid=1 and a first cache starts
the terminal byte-two read L edges later. Recheck a7/raw-valid then and accept
the pair atomically. Before this, neither byte is delivered. Any FAULT rejects
both, including a bad first/second stop after tentative capture. Raw-valid is
not frame acceptance and has no new rising transition on byte-two overwrite.

## Exact deadline and completion bound

Let C1,C2 be the oracle's raw capture edges: C2-C1=10P. First positive poll
delay d is in 0..H-1 for the defined settled integer-edge grid. Thus the first
copy occurs at C1+d+L and must be strictly before C2. Admission is:

`H>=1, L>=1, H+L<=10P`.

Then d+L<=H-1+L<=10P-1. At H+L=10P the worst phase reads on C2-1, the last
safe edge; increasing the bound by one can read on C2 and silently copy byte
two instead. At P434, the raw window is 4,340 clocks, 86.8 us at the target;
H=4,338,L=2 has last-safe first read at C2-1. The earlier 9P/78.12-us interval
starts at stop validation and is NOT the full raw quarantine window. No need
to observe the brief first-stop PC1 status: final HALT validates both frames.

For a good batch the pair is available by HALT+H-1+L <= HALT+10P-1. The second
raw byte is stable after HALT until forbidden mutation/reset. H/L bounds include
host transport/sample latency; if they cannot be justified physically, this
digital workload does not establish physical losslessness. Faster baud periods
shrink the window linearly and must be separately qualified.

Example execution edges, start_quarter=17, P434, H4338, L2, first_poll=3695:

| Edge | Public event/host action | Delivery state |
|---|---|---|
| 3695 | Poll sees raw-valid=0 | None |
| 3696 | Chip commits byte one; raw-valid becomes 1 | Not accepted |
| 4130 | Firmware validates first stop | Still not delivered |
| 8033 | Next poll sees raw-valid=1; schedule copy | None |
| 8035 | Copy raw byte one, one edge before overwrite | Tentative only |
| 8036 | Chip overwrites raw register with byte two; valid stays 1 | First survives only in host cache |
| 8470/8471 | Second stop validates / firmware HALTs at a7 | Both frames validated |
| 12371/12373 | Poll sees a7 / copy byte two and recheck a7/valid | Atomically accept both |

The poll-to-copy delay is included in L; selector access is not an extra
unbudgeted operation. At P434 the declared bit period is 8.68 us at the 50 MHz
target (derived 115,207.37 bit/s), not a measured physical baud rating.

## Falsification, accounting and limits

An independent register-visibility oracle (not Machine.edge) and public-pin
tests must cover last-safe H/L/residues, reduced P4, exact P434 input phases,
tentative-before-stop, first/second framing fault discard, abort, and an unsafe
same-edge-overwrite observation. Two different first bytes with the same
second byte produce identical late-reader observations; after overwrite the
unserved first byte is unrecoverable through this register interface.

An SMT arithmetic lemma checks the integer bound and produces a counterexample
for the one-edge-weakened bound. It is NOT an integrated RTL liveness or pad
timing proof. Existing RTL/synchronizer/readout formal obligations remain.

No chip storage or interface changes: E0018's generic result (2,793 cells/410
state bits) is reproduced by local/clean CI, not physical evidence. The host retains
two bytes and service/control state; this cost is explicitly outside CHIP_COMPLETE
and does not substitute for an autonomous on-chip queue. No general asynchronous
service, unserviced two-byte retention, full-duplex, or continuous RX claim.
