# K-INPUT-WAIT programmed-kernel acceptance

Status: acceptance frozen before implementation, 2026-10-03.

Question: can one program loaded through public pins observe a synchronized
external input, distinguish event from timeout without protocol-specific RTL,
and reach HALT on both paths within a declared cycle bound?

## Minimal semantic extension

`WAIT_PIN` bit `[25]` becomes `timeout_skip`; `[24:16]` remain zero. Existing
words with `timeout_skip=0` retain sticky FAULT on expiry. With
`timeout_skip=1`, an unmatched final observation edge clears the wait, adds two
to PC, and returns to RUN. A matching input still wins on that edge and adds one
to PC. This is the minimum one-instruction conditional control flow required by
the kernel; no protocol-specific RTL or general branch instruction is added.

The kernel is three words (96 used program bits in the 256-bit store):

| PC | Instruction | Purpose |
|---:|---|---|
| 0 | `WAIT_PIN(pin=2, level=1, timeout=4, timeout_skip=1)` | event advances to 1; timeout skips to 2 |
| 1 | `SET(mask=1, oe=1, value=1)` | observable event marker |
| 2 | `HALT` | common bounded terminal state |

## Falsifiable scenarios

Both scenarios load and read back the same three words solely through public
pins, leave load mode with input low, and hold `ena=0` for two flush edges.
Expected traces are generated independently from this table, not from RTL
internal state.

| Scenario | Accepted execution/observation edges after flush | Required public result |
|---|---|---|
| EVENT | execute PC0; external pin becomes high; two synchronizer-latency observations remain waiting; third observes event; execute SET; execute HALT | HALT at PC2, `uio_out[0]=1`, `uio_oe[0]=1` |
| TIMEOUT | execute PC0; four unmatched observation edges; execute HALT | HALT at PC2, `uio_out[0]=0`, `uio_oe[0]=0` |

EVENT must halt no later than six accepted engine edges after word-zero
execution. TIMEOUT must halt on the sixth accepted engine edge. A match on the
fourth timeout observation must take the event path. Disabled edges must change
neither PC nor timeout count.

After each path, sampled reset must clear engine outputs and erase the program.
The complete test must then reload the same image and exercise the other path.
Any trace mismatch, missing readback, non-HALT terminal state, late response,
protocol-specific RTL delta, or divergence between Icarus and Verilator is a
workload FAIL.

## Evidence boundary

A passing RTL trace is `PASS/MEASURED` only for K-INPUT-WAIT at the RTL rung and
for the declared 50 MHz digital model. It is not metastability/MTBF evidence,
CMOS5L area/timing, gate-level behavior, analog input behavior, or silicon proof.

