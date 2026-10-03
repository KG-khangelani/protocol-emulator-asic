# M1 public-pin program loader and readback contract

Status: implemented simulation candidate. This interface replaces the D9
constant preload and is the first `P-RELOAD` experiment. It is synchronous to
the project clock; it is not an asynchronous serial protocol and makes no
metastability claim.

## Public-pin transaction

`ui_in[7]` selects load mode. While load mode is high, the execution engine is
held in synchronous reset and GPIO ownership moves to the loader:

| Pin | Meaning in load mode |
|---|---|
| `ui_in[6]` | 1 = write on an accepted edge; 0 = combinational readback |
| `ui_in[5]` | 1 = program-length register; 0 = program byte |
| `ui_in[4:0]` | byte address 0..31 when selecting program data |
| `uio_in[7:0]` | write data |
| `uio_out[7:0]` | selected readback data |
| `uio_oe[7:0]` | `00` during writes, `FF` during reads |

The store contains eight provisional 32-bit words. Byte address `4*n + lane`
selects word `n`, bits `8*lane +: 8`; lane zero is the least-significant byte.
Program length is encoded in the low nibble and is valid from 1 through 8;
upper-nibble bits must be zero.

Reset clears all program bytes, length, and `program_ready`. Every program-byte
write clears `program_ready`, so length must be committed after all bytes. A
valid length write sets `program_ready`; an invalid length write clears length
and ready. Writes occur only on rising edges with `rst_n=1`, `ena=1`, load mode,
and write asserted. Readback is combinational and does not mutate state.

When load mode falls after a valid commit, the next accepted rising edge
executes word zero. Re-entering load mode resets the engine without erasing the
store. A sampled chip reset erases the store, so the demonstrated flow is:
reset, load A through public pins, run A, reset, load B, read B back, run B.

For a program whose first action depends on `uio_in`, loader data must first be
flushed from the shared input synchronizer: leave load mode, drive the intended
idle inputs, and hold `ena=0` for two rising edges before accepting word zero.
See `m1-input-wait.md`.

## Safety and evidence boundary

Fetching is valid only when `program_ready=1`, `pc < program_length`, and
`pc < 8`; otherwise the engine receives `instruction_valid=0` and enters its
defined FAULT state. Loader read cycles drive all eight bidirectional pins;
write cycles release them to avoid contention with the external source.

Passing `P-RELOAD` simulation demonstrates observable post-reset program change
without RTL changes. It does not establish nonvolatile retention, asynchronous
input safety, memory-macro area, physical timing, gate-level behavior, or
fabricated-silicon operation.
