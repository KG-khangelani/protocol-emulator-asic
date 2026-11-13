# D48 - Adopt the qualified SRAM programmable core

Date: 2026-11-13. Decision: adopt the exact E0045-qualified `od128-sram` design.

The original register-based od128 candidate passed the shared protocol matrix
but failed routing. Shared and banked read experiments and a clock-spacing
diagnostic did not close that gate. D42's synchronous vendor SRAM and look-ahead
fetch preserve instruction timing and the 128-word logical capacity while
removing the large register-memory routing burden. The complete mapped
footprint, including the real macro, is 78.5306% below D39 under matched
conditions. The allocated die remains 8x4; this is not a routed comparison to
the rejected D39 design.

Adopt the five exact E0042 RTL files and all twenty physical input files from
E0045's original `sram-physical-candidate` archive. Bind their hashes, the
qualification result, metadata, this decision, combined regression, complete
normal-command verification and corrected two-simulator netlist pair in
`tools/production-profile.json`. Any changed or missing input rejects reuse.
Default physical staging must check production before generation, then require
the regenerated files to equal the adopted files byte for byte. Preserve the
experimental workflow and move the unchanged G1 candidate workflow to
`gds-g1.yaml`; D34's archived configuration and G1/M0 qualifications stay frozen.

E0045's run43348171110 at
`94a30825c633778b8fb1b8374b79d1a419d3fc96` passes complete GDS, all ten
official prechecks and all eighteen real-netlist public groups. Its original
1,713 files and 55 producing inputs pass Windows and pinned Linux replay, and
five provenance/semantic corruption controls are rejected. The submitted
netlist is exactly the corrected Icarus/Verilator pair in E0043. Every public
SPI, I2C, boundary and abort reference record is unchanged.

The circuit has one general temporal engine, 353 register bits and one
8,192-bit physical SRAM exposing 128 logical 32-bit program words. Interface
0x22 makes program-byte readback clocked: present bank/address before a rising
edge and sample after it. Instruction timing and existing control/data register
reads remain unchanged. Banks 0..15, length 1..128, invalid-image cleanup,
reset-visible zero words and the word-zero shadow follow the frozen D37/D42
contracts. No protocol-specific RTL engine is added.

The complete thirty-group pair in E0042 and eight-stage normal-command CI in
E0044 qualify these same source/model hashes. Preserve source-matched engine
equivalence/reset, prefetch prediction, SRAM arbitrary-word induction/covers,
checked counterexamples and the separate historical formal baseline. Earlier
whole-chip timeouts remain inconclusive. Default production commands must
exercise the actual `src/` files and retain a fresh clean CI record; do not
substitute the experimental generator's source directory.

The 20 ns target has positive reported setup/hold margin under the pinned
model sets; it is not measured Fmax or silicon. D43-D47's power connections,
nine input buffers, public-pin guard, exact two-file Magic rule alignment and
selection of 54 existing full-height supply contacts remain explicit. All
original 80 stages and every acceptance gate remain. The fast set combines
-40 C standard cells with -55 C SRAM and is not isothermal characterization.

UART remains the qualified TX and bounded RX/host-service contracts, including
framing, phase, delivery and H+L<=10P limits. SPI retains both bit orders,
all four modes, its input-hold requirement and expected edge-only failures.
I2C retains its 7-bit, Standard-mode 100 kHz controller contract, external
pull-up/resolved-bus assumptions, clock stretching, final-edge priority and
bounded cleanup. Continuous autonomous UART, broad device interoperability,
analog signaling and fabricated hardware remain outside this decision.

Complete the actual-default-command audit and publish the qualified milestone
with original archives, matching source/image identity and verified downloads
before closing G2. G3-G6 remain separately ordered. G1's compact10 qualification,
P rejection, M0's original 6x4 evidence and pending owner fluency are unchanged.
