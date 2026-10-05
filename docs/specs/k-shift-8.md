# K-SHIFT-8 programmed-kernel acceptance

Status: acceptance frozen before implementation on 2026-10-05; implementation
head `d1ddc8a` passes exact-head CI and independent re-review in draft PR 4.

## Question and scope

Can the candidate send and receive one eight-bit payload in either bit order,
using only public-pin-loaded program and data, with every bit edge and terminal
condition bounded? This is a serializer/deserializer microkernel. It is not yet
UART, SPI, I2C, a protocol clock, or an electrical-compliance claim.

## Data registers and loader mapping

While `ui_in[7]=1`, `ui_in[5]=1` selects an eight-bit data/control register and
`ui_in[4:0]` selects its exact address:

| Address | Name | Write | Read | Reset |
|---:|---|---|---|---|
| 0 | program length | valid values 1..8 commit the image | `{4'b0, length}` | zero |
| 1 | TX payload | stores the next transmit byte and clears RX-valid | payload | zero |
| 2 | RX result | ignored | most recently completed receive byte | zero |
| 3 | RX status | ignored | bit 0 is RX-valid; bits 7:1 are zero | zero |
| 4..31 | reserved | ignored | zero | zero |

The existing program-byte space remains selected by `ui_in[5]=0`; address zero
length transactions remain backward compatible with P-RELOAD. Readback is
combinational. Writes require a rising edge with `rst_n=1`, `ena=1`, loader
mode, and write asserted. Entering loader mode resets the engine but preserves
program, payload, completed result, and RX-valid. Only sampled chip reset erases
them. A new TX payload write invalidates an older RX result.

## SHIFT_STEP encoding

Opcode `10` is divided by bit 29:

| Field | Meaning |
|---|---|
| `[31:30]=10`, `[29]=0`, `[28:0]=0` | HALT, unchanged |
| `[31:30]=10`, `[29]=1` | SHIFT_STEP |
| `[28]` | 0 = least-significant bit first; 1 = most-significant bit first |
| `[27:25]` | transmit GPIO pin |
| `[24:22]` | receive GPIO pin |
| `[21:0]` | reserved, must be zero |

Transmit and receive pins must differ. A reserved-bit violation, equal pins, or
a bit-order/pin change during an incomplete byte enters sticky FAULT at the
current PC without changing GPIO or committing a receive result.

## Accepted-edge behavior

The engine retains an eight-bit TX shift register, an eight-bit RX shift
register, three-bit completed-step count, active flag, and the latched order and
pin selection. A valid first SHIFT_STEP atomically:

1. loads the TX shift register from the public TX payload;
2. clears the in-progress RX shift register;
3. drives the selected payload bit on the TX pin and sets its output enable;
4. releases the RX pin and samples its synchronized value;
5. records one completed step and advances PC normally.

Each later matching SHIFT_STEP drives the next TX bit, samples the next RX bit,
and advances PC normally. Other GPIO pins retain value and direction. LSB-first
uses payload bits `0,1,...,7` and assembles received samples into result bits
`0,1,...,7`; MSB-first uses `7,6,...,0` for both transmit and receive.

On the eighth SHIFT_STEP, the engine clears active/count state and the external
RX register captures the completed byte on that same rising edge. The commit
condition and assembled data are combinational functions of pre-edge state; no
extra handshake register or hidden cycle is present. RX-valid is observable
immediately after that edge and is never asserted for a partial byte.

| Accepted edge | Before | Action | After |
|---|---|---|---|
| First SHIFT_STEP | inactive | drive/sample bit 0 in selected order | active, completed=1 |
| Middle SHIFT_STEP | active, completed 1..6 | drive/sample next bit | active, completed increments |
| Eighth SHIFT_STEP | active, completed=7 | drive/sample final bit and capture result | inactive, completed=0, RX-valid=1 |
| Following edge | complete | HALT may execute | terminal state, result retained |

`ena=0` consumes no SHIFT_STEP and freezes engine/GPIO shift state; the input
synchronizer continues sampling as already specified. Sampled chip reset aborts
a partial byte, clears engine/GPIO state and the data registers, and wins over
enable. Entering loader mode aborts a partial byte without asserting RX-valid.

SET, WAIT, and WAIT_PIN may execute between SHIFT_STEP instructions without
changing in-progress shift state. A bounded LOOP may repeat SHIFT_STEP and its
surrounding timing instructions. HALT while a byte is incomplete is invalid and
enters FAULT; HALT after the eighth step terminates normally. Existing nested
LOOP and timeout-skip restrictions remain unchanged.

## Falsifiable public-pin kernel

For each bit order, load and read back this three-word image and write/read a TX
payload through data-register address 1:

| PC | Instruction |
|---:|---|
| 0 | `LOOP(length=1, count=8)` |
| 1 | `SHIFT_STEP(order, tx_pin=0, rx_pin=1)` |
| 2 | `HALT` |

After loader exit, the first receive bit is held stable for two disabled flush
edges. Because the synchronized value consumed by the engine trails the public
pin by two sampling edges, the second receive bit is presented before LOOP and
each later future bit is presented two accepted edges ahead of its SHIFT_STEP.
This schedule is part of the oracle; raw `uio_in` is never treated as an
unsynchronized engine input.

The accepted execution bound is ten edges: LOOP, eight SHIFT_STEP executions,
then HALT. After every SHIFT_STEP, pin 0 must expose the corresponding TX bit
with output-enable one and pin 1 must be released. On HALT, loader reads must
return the exact reconstructed RX byte with status bit zero equal to one.

The retained cases are:

| Order | TX payload | Required TX sequence | RX stimulus/result |
|---|---:|---|---:|
| LSB-first | `0x96` | `0,1,1,0,1,0,0,1` | `0x3a` |
| MSB-first | `0x69` | `0,1,1,0,1,0,0,1` | `0xc5` |

Adversarial checks must reject equal TX/RX pins, reserved bits, a configuration
change after one step, and HALT after seven steps. They must also cover reset
from an active transfer, an injected disabled edge, both byte extremes, and
interleaved SET/WAIT state preservation. Icarus and Verilator must agree with an
independently structured semantic model; formal properties cover all engine
states and data-register capture/readback.

## Evidence boundary

Passing is `PASS`/`MEASURED` only for K-SHIFT-8 at the RTL-simulation rung. The
kernel uses 96 program bits plus the reusable eight-bit TX, eight-bit RX and
valid state. Generic synthesis is structural screening only. No protocol,
metastability/MTBF, gate-netlist, CMOS5L fit/timing, analog, or silicon result is
implied.
