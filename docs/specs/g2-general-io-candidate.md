# G2 general I/O candidates - predeclared experiment

Status: **implemented isolated experiment; D37 advances od128 to remaining G2
gates**, 2026-11-12. E0035 retains scoped results, failures and exact source
identities. The D36 I2C acceptance contract and oracle remain unchanged.

## Evidence motivating the experiment

E0033 shows that existing timeout skip can reach inline cleanup, but the same
wait inside a LOOP faults and holds SDA low. Its literal write-wire list needs
122 words, before conditional ACK rejection or timeout cleanup. E0034 proves
that the existing SHIFT_STEP can receive SDA with TX zero pulling SCL low;
all bytes pass both simulators. No dedicated I2C state machine is needed to
obtain those behaviors.

Compare two complete-chip experiments. Both retain compact10's legacy core,
loader, data registers, input synchronizer and compact DRIVE/SAMPLE operations.
Both add general conditional timeout branching and an eight-bit PC. The
`literal255` control uses 255 program words and literal SET output directions.
The `od128` candidate uses 128 words and two general serial-output option bits.
These capacities follow the complete image listings, not a minimum-size claim.
Physical area, timing and feasibility remain measurements.

## General bounded branch

WAIT_PIN retains opcode 11, pin[29:27], level[26] and count[15:0]. Bit 24 enables
an absolute failure destination in [23:16]. Bit 25 (legacy timeout skip) must
be zero when the new branch is enabled. Without bit 24, [23:16] must remain
zero and all prior WAIT_PIN behavior is retained.

Input match wins on the final observation edge. A mismatch at count zero, or
expiry of a nonzero wait, branches to the declared destination. This branch
abandons any active LOOP and incomplete manual/burst/phase shift, clears wait
and prepared-phase state, and resumes RUN at the destination without changing
GPIO or the public completed RX/valid registers. Firmware performs cleanup.
Successful waits retain ordinary LOOP/shift state. Reset/loader entry clear
the latched branch mode and destination. Disable freezes them with the wait.

An out-of-range destination reaches the normal invalid-fetch FAULT; no address
bits are silently truncated. Legacy timeout skip inside LOOP continues to
fault. A legacy two-word skip that overflows the eight-bit PC faults at its
current address; it must not wrap to zero. This is a generic conditional
abort/branch, not an I2C timeout circuit.

## General serial output options in od128

Manual SHIFT_STEP and compact DRIVE assign formerly reserved bit 0 to
open-drain output and bit 1 to initial alternate-payload selection. Burst and
SAMPLE encodings retain their previous meanings and reserved-bit rules.

With bit 0 zero, TX output behavior is unchanged. With it one, TX output value
is zero and output enable is the inverse of the selected transmit bit: zero
pulls low, one releases. RX direction and capture semantics are unchanged;
TX and RX pins must still differ. Compact DRIVE's auxiliary GPIO still obeys
its existing mask/value semantics and exclusion of TX/RX pins.

Bit 1 chooses TX payload register 4 instead of register 1 only when beginning a
new manual/phase byte. Later steps use the already latched shifter. Open-drain
mode is a per-drive option; changing it between bits has the explicitly selected
electrical behavior. Existing order/pin/phase consistency checks remain.
Neither option adds a dedicated protocol engine or changes input synchronization.

## Public storage and status

PC, loop start/end and program length widen to eight bits. LOOP body length and
count stay five and eight bits; the wide loop-target calculation detects
overflow instead of wrapping. Normal uo_out retains state[7:6], ready[5] and
the low five PC bits. Runtime selector 6 returns the full eight-bit PC; selector
7 identifies this experimental interface as 0x21 (od128) or 0x20 (literal255).
Existing runtime selectors 1..5 remain; writes to 6/7 remain ignored.

The public program bank at register 5 selects groups of eight words. od128
accepts bank values 0..15 and lengths 1..128. literal255 accepts banks 0..31
and lengths 1..255; its last bank's final word is unallocated. Invalid bank
selection resets the bank to zero, clears length/ready; every bank selection
invalidates the current image. A valid length commit resets the bank to zero.
Out-of-capacity byte writes do not alias another word, and read back zero.
Reset clears the actual allocated store; there is no abstract preload shortcut.

The eight-bit PC has a representable invalid-fetch sentinel for both stores.
Legacy images remain byte-compatible within their prior valid domain. Accepting
larger lengths, assigning new serial/branch encodings and runtime selectors is
an intentional interface extension, not full legacy rejection compatibility.
No Tiny Tapeout external pin or physical-flow setting changes are proposed.

## Predeclared comparison and gates

`experiments/i2c/general_programs.py` emits complete experimental images using
only generic instructions. Address, transmit byte and kind vary through public
program/data inputs. RX byte, ACK decisions and stretching are external target
inputs and never determine the program image. The combined serial schedule
overrides the read address's final R/W bit with a normal SET during SCL low.

1. Retain image words, labels, storage, measured wire timing and failures. Check
   every complete transaction using the existing independent I2C oracle.
2. Test public load/readback across the real banks, final-edge priority, timeout
   cleanup from inside loops/partial shifts, NACK branches, raw-result lifetime,
   reset/disable/loader interventions, all bytes and meaningful wrong programs.
3. Require both simulators and relevant formal assertions. Add instruction and
   public-storage boundary checks; preserve legacy UART/SPI premises and controls.
4. Compare complete-chip generic and mapped cost with actual store/loader state.
   Select a candidate from observed behavior and cost. A reference list or
   generic synthesis does not prove mapped/routed timing or physical fit.
5. G2 promotion still requires the full mandatory matrix and fresh pinned 8x4
   CMOS5L routing, timing, precheck and real-netlist public-pin evidence at the
   same candidate revision, followed by verified milestone publication.

Do not relax the frozen I2C oracle, physical limits or UART/SPI boundaries to
obtain a passing candidate. Retain an infeasible result and revise the general
instruction/storage design with a new measured decision if necessary.
