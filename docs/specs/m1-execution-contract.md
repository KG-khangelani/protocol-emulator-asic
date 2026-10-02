# Proposed M1 SET/WAIT/HALT execution contract

Status: **proposal for review; not implemented and not an M1 gate result**.
M0 remains active until its owner-fluency checkpoint passes. This document is
the separately permitted semantics draft for M1-T01. It defines observable
cycle behavior without selecting an instruction encoding, program-memory size,
loader, or storage technology.

## Scope and terminology

The proposed machine has an unsigned program counter `pc`, an execution state
`RUN`, `WAIT`, `HALT`, or `FAULT`, an unsigned wait counter `wait_left`, and one
eight-bit logical GPIO bank with `gpio_value` and `gpio_oe`. An **accepted edge**
is a rising edge of `clk` at which `rst_n = 1` and `ena = 1` are sampled.

The abstract program is an ordered, finite sequence of decoded instructions.
Its valid addresses are `0 .. program_length - 1`; `program_length = 0` is
allowed and faults on the first accepted fetch. The program and its declared
length are stable from release of reset until the next reset. Loading,
readback, encoding, fetch-memory latency, and public-pin mapping are deliberately
outside this proposal and must be specified before production RTL. A concrete
implementation may pipeline or encode differently only if its public pins and
architectural state match this edge contract exactly.

The only valid decoded instructions are:

- `SET(mask, value, oe)`, with three eight-bit operands.
- `WAIT(count)`, where `count` is an unsigned representable value.
- `HALT`, with no operands.

Reserved opcodes, reserved operand bits, malformed instructions, and a fetch
outside the declared program are invalid. There is no implicit PC wrap.

## Edge priority and state transition

At every rising edge, exactly the first applicable row is taken:

| Priority | Sampled condition | State immediately after the edge |
|---:|---|---|
| 1 | `rst_n = 0` | `pc = 0`, `state = RUN`, `wait_left = 0`, `gpio_value = 0`, `gpio_oe = 0` |
| 2 | `rst_n = 1`, `ena = 0` | Hold every architectural register and GPIO control bit |
| 3 | `state = HALT` | Hold every architectural register and GPIO control bit |
| 4 | `state = FAULT` | Hold every architectural register and GPIO control bit |
| 5 | `state = WAIT` | Apply the WAIT completion rule below |
| 6 | `state = RUN` | Fetch at `pc`; execute one valid instruction or enter `FAULT` |

Reset is synchronous, active low, and has priority over enable and every machine
state. Power-up state is unspecified until reset is sampled on a rising edge.
Changing inputs between rising edges has no architectural effect. `ena = 0`
freezes time: it neither decrements a wait nor refetches/retires an instruction.

## Instruction semantics

### SET

On its accepted execution edge, `SET(mask, value, oe)` atomically updates:

```text
gpio_value' = (gpio_value & ~mask) | (value & mask)
gpio_oe'    = (gpio_oe    & ~mask) | (oe    & mask)
pc'         = pc + 1
state'      = RUN
wait_left'  = 0
```

All expressions are eight-bit for GPIO fields. Unmasked pins retain both their
stored value and direction. A pin with `gpio_oe[i] = 1` drives
`gpio_value[i]`; a pin with `gpio_oe[i] = 0` is released (high impedance) and
its stored value is not externally driven. Value and direction change together
after the same edge; the contract promises no ordering or analog glitch
behavior within that edge. SET never reads an input pin and does not detect
contention. Open-drain operation can be expressed only by storing value zero
and toggling output enable; driving one is not open-drain behavior.

### WAIT

`WAIT(count)` delays the next instruction by exactly `count` subsequent
accepted edges. On the accepted execution edge:

- if `count = 0`, set `pc = pc + 1`, keep `state = RUN`, and keep
  `wait_left = 0`;
- if `count > 0`, keep `pc` at the WAIT address, set `state = WAIT`, and set
  `wait_left = count`.

On each later accepted edge in `WAIT`:

- if `wait_left > 1`, decrement it and change nothing else;
- if `wait_left = 1`, set it to zero, advance `pc` by one, and enter `RUN`.

The instruction after WAIT executes on the next accepted edge after completion.
Thus the number of accepted edges from the WAIT execution edge through the next
instruction's execution edge is `count + 1`. GPIO controls hold throughout.
Reset aborts a wait; disabled edges do not count. `WAIT` is cycle delay only in
this subset: pin-event waits and timeouts remain future semantics and must not
be inferred from this name.

| Program | Accepted edge 1 | Edge 2 | Edge 3 | Edge 4 | Edge 5 |
|---|---|---|---|---|---|
| `WAIT(0); SET` | WAIT completes, `pc=1` | SET commits | next instruction | - | - |
| `WAIT(1); SET` | enter WAIT, left=1 | complete, `pc=1` | SET commits | next instruction | - |
| `WAIT(2); SET` | enter WAIT, left=2 | left=1 | complete, `pc=1` | SET commits | next instruction |

### HALT

On its accepted execution edge, HALT enters `HALT`, keeps `pc` at the HALT
address, clears `wait_left`, and holds GPIO controls. No later instruction is
fetched or executed, irrespective of enable toggling. Only sampled reset exits
HALT. HALT is normal termination and is distinguishable from invalid-program
termination by `state`.

### Invalid program behavior

If `state = RUN` and `pc` is outside the declared program, or the fetched word
does not decode to a valid instruction and operands, that accepted edge enters
`FAULT`. The faulting `pc` is retained, `wait_left` becomes zero, and GPIO
controls retain their pre-edge values. FAULT is sticky until sampled reset.
There is no trap vector, skip, implicit HALT, memory wrap, or execution of a
default all-zero instruction. This fail-closed rule makes truncation and corrupt
programs observable in verification rather than silently changing timing.

## Complete timing examples

Each cell is architectural state immediately after the named rising edge.

| Stimulus/program | Reset edge | Accepted 1 | Accepted 2 | Accepted 3 | Accepted 4 |
|---|---|---|---|---|---|
| `SET(01,01,01); WAIT(1); HALT` | RUN pc0, pins released | RUN pc1, pin0 drives 1 | WAIT pc1 left1 | RUN pc2 | HALT pc2 |
| Same, `ena=0` on edge 3 | RUN pc0 | RUN pc1 | WAIT pc1 left1 | unchanged | RUN pc2 after re-enable |
| `SET;` then out-of-range | RUN pc0 | RUN pc1, SET visible | FAULT pc1, pins hold | FAULT pc1 | FAULT pc1 |
| invalid opcode at address 0 | RUN pc0 | FAULT pc0, pins released | FAULT pc0 | FAULT pc0 | FAULT pc0 |
| HALT, then reset with `ena=0` | RUN pc0 | HALT pc0 | HALT pc0 | reset: RUN pc0, pins released | held RUN pc0 if reset released and disabled |

## Verification obligations before implementation acceptance

The proposal is acceptable for production only when independent checks cover:

1. A semantic trace model predicts every edge for all three instructions,
   including consecutive SET/WAIT/HALT sequences.
2. Reset from RUN, every WAIT count boundary, HALT, and FAULT wins over enable
   and produces the exact reset state on the sampled edge.
3. Random disabled spans freeze PC, wait count, state, value, and direction;
   re-enable resumes without consuming a hidden cycle.
4. WAIT counts 0, 1, 2, and the maximum representable value have exact edge
   counts, with no underflow or off-by-one execution.
5. SET exhaustively or property-wise preserves unmasked bits and commits masked
   value/direction atomically; released pins are never judged by stored value.
6. HALT and every invalid-program class are sticky, retain the specified PC and
   GPIO state, and recover only through reset.
7. Program-length boundaries include empty, one-instruction, exactly-last-word,
   and fall-through beyond the last instruction. PC arithmetic overflow cannot
   alias a valid address.
8. Formal properties cover priority, stability, wait progress under accepted
   edges, SET masking, and sticky terminal states without assuming friendly
   inputs. At least one mutation or intentionally wrong model must fail.
9. RTL simulation compares public pins against an independently structured
   oracle with retained seeds and minimal failing traces. Encoding, memory
   latency, loader, synchronizers, and public-pin mapping receive their own
   contracts before they are counted as implemented.
10. Results use the evaluation contract's statuses and boundaries. These
    specification checks are semantic evidence only: they are not RTL,
    synthesis, CMOS5L, timing, gate-level, or silicon evidence.

## Evaluation-contract reconciliation

This subset can exercise SET pin traces and deterministic delays, but it cannot
yet satisfy `K-INPUT-WAIT`, `K-SHIFT-8`, `K-BOUNDED-LOOP`, `P-RELOAD`, or any
mandatory protocol workload. It therefore must not be presented as a complete
candidate. CHIP_COMPLETE accounting remains the primary boundary, and program
storage, loader/readback, synchronization, pin mapping, and queues remain
`NOT_EVALUATED`. The 50 MHz clock remains an experimental target, not a proven
maximum or a promise of protocol bitrate.

