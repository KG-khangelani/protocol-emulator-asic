# K-BOUNDED-LOOP programmed-kernel acceptance

Status: acceptance frozen before implementation, 2026-10-03.

## Selection rationale

K-BOUNDED-LOOP precedes K-SHIFT-8. A bounded counted block directly compresses
repeated SET/WAIT schedules shared by UART, SPI and I2C. K-SHIFT-8 additionally
needs a defined payload/register loading path, shift direction, sampling phase
and received-data observation path. Adding those together would obscure which
state is actually necessary. This ordering is not a permanent rejection of a
shifter.

## LOOP encoding and execution

Opcode `01` with `[29]=1` is `LOOP`; ordinary WAIT retains `[29:16]=0`.
LOOP encodes body length `[28:24]` (1..31 words), reserved `[23:8]=0`, and
iteration count `[7:0]` (0..255). The body is the immediately following
`length` words and nesting is invalid.

- Count zero skips the body in the LOOP execution edge.
- Nonzero count latches body start/end and remaining iterations, then advances
  to the first body word.
- Completion of the final body word returns to body start while more iterations
  remain; otherwise it clears loop state and advances past the body.
- Reset aborts and clears loop state. Disabled edges freeze all engine state.
- HALT, another LOOP, or timeout-skip control flow inside an active body faults.
  SET, WAIT and the event path of WAIT_PIN use normal counted-body completion.
- The six-bit `PC + 1 + length` target is range-checked before narrowing. A
  target above 31 faults at the LOOP PC; it must never alias through PC wrap.

## Falsifiable kernel

For each count 0, 1, 2 and 255, load and read back this four-word image through
public pins after reset:

| PC | Instruction |
|---:|---|
| 0 | `LOOP(length=2, count=N)` |
| 1 | `SET(mask=1, oe=1, value=1)` |
| 2 | `SET(mask=1, oe=1, value=0)` |
| 3 | `HALT` |

An independent expected trace requires exactly `N` high/low GPIO pairs, then
HALT at PC3. The accepted-edge bound from LOOP execution through HALT is
`2*N+2`: two edges for each body iteration, plus LOOP and HALT. Count zero must
produce no driven transition. A disabled edge injected during count two must
not consume an iteration. Count 255 must produce exactly 510 body edges and
halt on accepted edge 512.

Any mismatch, overrun, wrap, non-HALT terminal state, nested-loop acceptance,
failure to erase/reload, simulator disagreement, or protocol-specific RTL delta
is FAIL. Passing simulation is RTL evidence only, not CMOS5L fit or timing.
