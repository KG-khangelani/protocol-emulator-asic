# Instruction set: od128-sram-v1

This guide describes the unchanged production engine, interface **0x22**.
It consolidates the historical instruction contracts for the current 128-word
SRAM profile. The implementation is [m1_engine.v](../src/m1_engine.v), and the
versioned encoder is [assembler.py](../tools/assembler.py). The
[programming guide](programming.md) explains source syntax and loading.

## Words, edges and state

Each instruction is 32 bits, stored as four little-endian bytes. PC is eight
bits, but loaded instructions occupy addresses 0..127 and execution must
remain below the committed length. Invalid fetch or instruction sequencing
enters FAULT. There are no general arithmetic registers, stack, interrupts or
unconditional jump instruction. A WAIT_PIN timeout can branch to an absolute
word address, including backward addresses; such programs need a separate
termination argument.

Instruction timing counts accepted rising edges with reset released, ready,
loader mode off and enable high. If an instruction executes at edge e and has
spacing d, the next instruction executes at e+d. Disabled edges do not consume
waits or shift bits, although input synchronization continues. Fixed-rate
protocol examples require uninterrupted enable during their judged trace.

Ordinary status is `{state[1:0], ready, pc[4:0]}`. State codes are 0=RUN,
1=WAITING, 2=HALTED and 3=FAULTED. HALT/FAULT hold PC and GPIO state until an
engine reset; they do not automatically release pins or clear the last result.
Chip reset and loader entry reset engine state on a rising edge, with reset
priority over enable. Their different storage effects are described in the
[architecture guide](architecture.md).

## Instructions and timing

| Source instruction | Meaning | Spacing to next instruction |
|---|---|---:|
| `SET mask=M value=V oe=E` | Replace GPIO value and output-enable bits selected by M; preserve other bits | 1 |
| `WAIT cycles=N` | Hold outputs and consume N additional accepted edges | N+1 |
| `HALT` | Enter terminal HALTED if no loop or partial shift remains | Terminal |
| `WAIT_PIN pin=P level=L timeout=N on_timeout=...` | Observe synchronized input, then wait at most N additional edges | 1..N+1 |
| `LOOP count=C end=label` | Repeat the following body C times; label is its exclusive end | 1 dispatch, then body |
| `SHIFT_STEP tx=T rx=R order=lsb/msb` | Drive and capture one bit; eight matching steps complete one byte | 1 |
| `SHIFT_BURST tx=T rx=R order=lsb/msb period=P` | Drive/capture eight bits, P edges apart, then hold through the final period | 8P |
| `DRIVE tx=T rx=R order=lsb/msb mask=M value=V` | Drive the next serial bit and auxiliary GPIO; prepare a later sample | 1 |
| `SAMPLE tx=T rx=R order=lsb/msb delay=N` | Capture the prepared bit after N accepted edges | N+1 |

M, V and E are bytes. Pin numbers are 0..7 and TX must differ from RX.
WAIT, WAIT_PIN and SAMPLE counts are 0..65535. Burst period is 2..65535.
LOOP count is 0..255; its body contains 1..31 words. There is no hidden
loop-back instruction or extra edge between body repetitions. Count zero skips
the body on the dispatch edge. An active loop cannot nest another loop or
terminate with HALT.

SHIFT_STEP and DRIVE accept optional `drive=push_pull/open_drain` and
`payload=TX0/TX1`; their defaults are push-pull and TX0. The first drive of a
byte latches its selected payload. Later drives use that shift state, so the
payload selector has no effect partway through the byte. Open-drain mode is
selected on each drive: bit zero drives low, bit one releases TX, and the
output value stays zero. RX is released for both drive styles.

SHIFT_STEP drives and samples on the same edge. DRIVE samples nothing; it must
be followed by a matching SAMPLE before the next DRIVE. SAMPLE with delay zero
captures on its own execution edge; delay N captures at e+N. The next
instruction follows one edge later. Order and pins must remain consistent
through a byte. DRIVE's auxiliary mask must exclude TX and RX; selected
auxiliary pins become outputs carrying the selected value.

A fresh SHIFT_BURST is push-pull and starts from the internal payload slot:
TX0 after reset, then TX1, alternating after each completed burst. Captures
occur at e, e+P, ..., e+7P; the following instruction executes at e+8P.
A burst cannot begin during a partial manual or phase transfer.

The eighth sample commits the assembled RX byte and sets raw-valid on that
same rising edge. SET, WAIT and a successful WAIT_PIN can be interleaved with
manual or phase shifting. HALT during an incomplete byte faults. Protocol
acceptance still requires the program's framing, bus and terminal checks.

## Input-wait outcomes

WAIT_PIN tests the synchronized level on dispatch. A match advances normally;
otherwise a nonzero timeout starts a countdown. A match on the final allowed
observation edge wins over expiry. Timeout zero makes one immediate decision.

| `on_timeout` | Mismatch at expiry |
|---|---|
| `fault` (default) | Enter FAULT at the current PC |
| `skip` | Continue at PC+2; invalid inside an active LOOP or if the addition overflows the PC |
| A label or word address | Abandon loop, partial shift and prepared phase; resume RUN at that address |

The absolute branch preserves GPIO and the completed RX/valid registers.
Firmware at the destination must perform any bus cleanup. The assembler
requires a destination within the loaded program. Raw hardware encodings with
an out-of-range destination fault on the subsequent invalid fetch.

## Exact encoding

All unassigned bits below must be zero. `|` is bitwise OR and `<<` is left
shift. No field is truncated by the assembler.

| Instruction | Word expression |
|---|---|
| SET | `(M << 16) | (E << 8) | V` |
| WAIT | `0x40000000 | N` |
| HALT | `0x80000000` |
| LOOP | `0x60000000 | (B << 24) | C`, where `B = end - PC - 1` |
| WAIT_PIN, fault | `0xC0000000 | (P << 27) | (L << 26) | N` |
| WAIT_PIN, skip | Fault encoding plus bit 25 |
| WAIT_PIN, absolute | Fault encoding plus bit 24 and `(destination << 16)`; bit 25 stays zero |

The serial family has common base
`S = 0xA0000000 | (O << 28) | (T << 25) | (R << 22)`.
O is 0 for LSB first and 1 for MSB first. D is 0 for push-pull and 1 for
open-drain. Q is 0 for TX0 and 1 for TX1.

| Serial instruction | Word expression | Required zero bits |
|---|---|---|
| SHIFT_STEP | `S | (Q << 1) | D` | 21..2 |
| SHIFT_BURST | `S | (1 << 21) | (P << 5)` | 4..0 |
| DRIVE | `S | (1 << 19) | (M << 11) | (V << 3) | (Q << 1) | D` | 21, 20, 2 |
| SAMPLE | `S | (2 << 19) | (N << 3)` | 21, 19, 2..0 |

LOOP reserves bits 23..8, requires a nonzero body length and detects a
nine-bit end-address overflow. With WAIT_PIN absolute mode off, bits 23..16
are zero. SET reserves bits 29..24; WAIT reserves bits 29..16. HALT has no
operand bits. Unsupported encodings and invalid runtime shift sequences fault
without applying that invalid instruction's GPIO update or RX commit.

The assembler additionally rejects nested active-loop structure, HALT or
legacy timeout skip inside a nonzero loop, unknown fields, out-of-image
branches and images longer than 128 words. Encoding validation alone cannot
prove every possible control-flow path has a valid shift sequence.

## Public data and control registers

All selectors below are hexadecimal. Loader reads use `ui_in=A0 | address`;
loader writes use `E0 | address` and the byte on `uio_in`. Runtime reads use
`60 | address` and return on dedicated `uo_out`, without entering loader mode.

| Address | Loader write | Loader read | Runtime read |
|---:|---|---|---|
| 0 | Commit length 1..128; invalid values clear ready and length | Program length | Zero |
| 1 | Set TX0; clear raw-valid | TX0 | TX0 |
| 2 | Ignored | Last completed RX byte | Last completed RX byte |
| 3 | Ignored | Bit 0 raw-valid; remaining bits zero | Same |
| 4 | Set TX1; clear raw-valid | TX1 | TX1 |
| 5 | Select bank 0..15 and invalidate ready/length | Current bank | Current bank |
| 6 | Ignored | Full PC | Full PC |
| 7 | Ignored | Interface identity 0x22 | Interface identity 0x22 |
| 8..31 | Ignored | Zero | Zero |

An invalid bank value selects bank zero and still clears ready/length.
Reset clears both payloads, RX and raw-valid. Payload writes clear raw-valid
but leave the RX byte itself unchanged. Neither loader entry nor a timeout
branch by itself erases a previously completed result. Read the
[loading plan and ownership rules](programming.md) before driving these pins.
