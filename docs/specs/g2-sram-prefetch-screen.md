# G2 synchronous SRAM and look-ahead fetch screen

Predeclared 2026-11-12 after E0041's completed routing diagnostic. This is an
isolated candidate experiment; D39, production, the frozen protocol oracles
and the existing physical qualification records remain unchanged.

## Motivation and installed inputs

D39's 4,278 sequential cells alone occupy 209,574.0864 square micrometres.
Removing sixteen clock NDR assignments avoids the early router error but
leaves 159,781 overflow, with Metal3 demand at 152.09% of resources. The
banked combinational alternative costs 5.20216% more mapped area. A storage
implementation change is justified before another full physical attempt.

The installed, pinned PDK 89d42ee6d2fd9b50b86a1aada6fee6673c3e6008 includes
`RM_IHPSG13_1P_256x32_c2_bm_bist`, a synchronous single-port bit-masked SRAM.
Its LEF footprint is 416.64 by 118.78 micrometres, or 49,488.4992 square
micrometres. Its 8,192 physical bits are not the proposed logical capacity:
the candidate exposes only 128 words / 4,096 bits. Footprint is not a measured
whole-chip saving. The [official FAQ](https://blog.janestreet.com/protocol-emulator-asic-competition/#faq),
checked on 2026-11-12, permits IHP SRAM subject to fit and precheck.

Use the exact installed macro and core functional-model bytes, retain their
hashes and license notices, tie A_DLY high, and tie all unused BIST inputs low.
No generated clocks: A_CLK is the public clock. Synthesis must instantiate the
actual macro as a macro, not silently remap the behavioral array into flops.

## Explicit interface revision

Keep D39's instruction encodings, banks 0..15, lengths 1..128, invalid-bank
cleanup, invalid-fetch fault, byte order, reset-visible zero bytes, write
qualification and public pin ownership. Identify the experimental interface
as **0x22** at runtime register 7. Existing control/data register reads remain
combinational. Only program-byte readback changes: the host presents a stable
bank/address before a rising edge and samples the returned byte after that
edge. Reads work with either ena value; writes still require rst_n and ena.
A new program-byte address is not promised to affect readback before an edge.
The original 0x21 combinational-read interface remains a separate profile.

The SRAM has no reset. Reset a 128-bit word-valid vector instead; an unwritten
word reads as zero. The first byte write to an invalid word writes a complete
zero-filled word with that byte inserted. Later writes use the byte mask.
Reset wins over writes and invalidates every logical word regardless of ena.
Check arbitrary unwritten bytes and reset/reload, not just fully written images.

Keep a 32-bit word-zero shadow, reset to zero and updated by the same accepted
byte writes. Execution at PC0 uses this shadow, preserving word-zero execution
on the first accepted edge after leaving load mode, including after high-bank
readback. Other PCs use the SRAM's registered read result with a registered
address/valid tag; stale or out-of-range fetch must never execute a different
word. The shadow is real implementation cost, not an abstract preload.

Expose the engine's combinational next PC to the store. Read that address at
the same edge that commits the engine state, so the next instruction is ready
for the following edge. Preserve all current reset/disable, LOOP, zero-length
wait, final-edge match, conditional cleanup, burst/phase and fault behavior.
No extra accepted instruction cycles or dedicated UART/SPI/I2C hardware are
allowed. Input synchronizers and the current host-service/input-hold limits
remain unchanged.

## Bounded first gates

1. Refactor the engine into explicit next-state logic without changing any
   sequential bit. On the original D39 complete-chip/store connection, prove
   all actual state and all public outputs equivalent, with a separate reset
   base. Use at most 120 seconds for temporal induction and 60 for reset,
   retaining source/model/log hashes and failures. This proves the refactor,
   not SRAM integration.
2. Implement the real macro wrapper. Exercise both simulators with the vendor
   functional model: all 512 byte addresses, all lanes, zero after reset,
   partial first writes, disabled writes, bank/length boundaries, clocked
   readback, word-zero shadow and fetch tags. Require a passing baseline and
   actual reset/alias/prefetch faults with observed counterexamples. Do not
   accept compilation failure as a negative-control success.
3. Prove the logical memory/validity relationship under arbitrary public writes
   and resets, without assuming loaded constants or excluding the real store.
   State the macro's trusted digital model boundary explicitly. Attempt a
   bounded 300-second proof per declared task; preserve timeouts. Then run the
   complete current/public protocol matrix against unchanged wire oracles in
   both simulators, using only the explicit 0x22 loading contract adaptation.
4. Only after those checks, measure the complete chip with the real macro,
   wrapper, shadow and all control state. Record generic logic separately
   from macro bits/footprint. A mapped result does not qualify physical fit.

## Physical decision still required

Macro placement, power, timing-library selection, precheck and actual-netlist
simulation need a separate frozen physical integration decision before a full
run. The installed SRAM fast library is characterized at 1.32 V / -55 C;
the existing standard-cell fast library is 1.32 V / -40 C. Do not silently
rename the SRAM library as a -40 C characterization or claim an unmeasured
temperature condition. Resolve and document that modeling boundary explicitly.
Keep the 8x4 footprint, 20 ns target and every timing/electrical/antenna/DRC/LVS
acceptance limit. G2 promotion and publication require fresh complete evidence
for the exact accepted candidate and its declared physical inputs.

## Refactor proof-order follow-up

The first whole-chip refactor attempt reaches its 120-second temporal limit
after the simple equivalence pass and as induction starts. Retain that failed
attempt. Try one separate induction-first run within the same 120-second
budget, keeping every state/output comparison, free input and independent
reset-base obligation. This changes proof scheduling, not the claim, models,
RTL, reset assumption or acceptance criterion.

That induction-first whole-chip attempt also times out. Do not keep extending
the monolithic run. Use a separate compositional proof: compare every actual
engine state bit and every original engine output for arbitrary instruction,
input, payload, reset and enable values, with an independent reset base. The
extra prefetch output is outside the old engine interface; its integration is
covered by the subsequent SRAM tests/proof. Require exact byte identity for
the top, store, data store and synchronizer surrounding the refactored engine
in this comparison. Equal engine outputs with those unchanged connections
establish the original chip's behavior by composition. Keep both monolithic
timeouts visible and label the changed proof scope explicitly. Bound this
engine induction to 120 seconds and its reset base to 60 seconds.
