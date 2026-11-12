# E0030 - Timed GPIO comparison

Frozen 2026-11-12, baseline d29460b8f04607d815c59a18febbf88c70607bbb.
Production src/, the historical compact builder, pins, H25, CS setup/hold,
HELD_RESPONSE and the eight-word public loader remain immutable inputs.

## Encodings and accepted-edge semantics

P: SET [29:24] is unsigned post-delay 0..63. DRIVE [2:0] selects
post-delay 4*k, k=0..7. F: SET [29] is pre-delay when one, post-delay when
zero; [28:24] is delay 0..31. Zero delay is immediate for either F selector.
All other fields and legal old encodings retain their meanings.
SAMPLE low bits remain reserved. DRIVE still rejects overlapping auxiliary
and TX/RX masks, duplicate preparation and mismatched phase configuration.

Delay N occupies its issue edge and N subsequent enabled edges. PC/loop
advance once on completion. Post actions update GPIO/direction (and DRIVE
TX preparation) once at issue. F pre-actions latch the final 8-bit GPIO and
8-bit direction values plus a pending flag, then apply both on completion.
Pending operations never re-read instruction operands. Disabled edges freeze
all state; reset wins, releases engine GPIO and cancels pending operations.
Loader entry resets the executor according to the existing ownership contract.
No delayed GPIO action produces an RX commit.

The D30 note calling SET's high bits ignored was incorrect: actual set_valid
requires [29:24]==0. New allocations intentionally change rejection of those
words. They do not preserve all formerly-invalid-word behavior.

## Four designs and programs

Generate separate compact8, compact10, P and F directories under build/.
compact8 is byte-identical to the E0029 compact copy. compact10 combines that
same compact engine with the historical ten-word banked top/store. It is not
the historical plain-phase banked engine. P/F keep the original eight-word
store/top and alter only their isolated engine copies.

Both modes 1/3, both orders use eight words:
SET idle; SET CS low/post23; LOOP(length3,count8); DRIVE; SET trailing;
SAMPLE(delay23); SET release; HALT.
P adds post24 to DRIVE. F adds pre24 to trailing SET. GPIO masks/direction
are the same as the old explicit-idle ten-word reference.
CS=2, leading=27+50*j, wire sample=52+50*j, capture=76+50*j,
release=427, HALT=428. P/F intermediate RUN/WAIT status can differ.
The compact10 reference executes the original ten words with identical
SPI pins, received byte/valid and terminal timing.

## Qualification and fixed budgets

Reference sweep per P/F: 3,072 paired-byte cases: modes1/3, both orders,
256 RX values, TX=(73*RX+19) modulo256, earliest/latest/mixed responses.
Public positive cases per P/F/compact10 and simulator: 1,024 byte-alphabet
cases with mixed responses rotated by RX modulo8, plus12 fixed corner cases
(early TX96/RX69, late TX00/RXff, mixed TXff/RX00 per mode/order).
Use both simulators, actual serial loading and readback, and the unchanged
independent external oracle. Require identical full records/traces across
simulators for each variant. Compare only SPI pins/OE/RX/valid/terminal
across variants, not intermediate execution status.

Exercise all encoded delays, GPIO/direction masks, instruction changes during
waiting, loop completion, disabled/reset/loader-abort cuts including the final
pending edge, invalid pins/reserved SAMPLE and invalid/mixed operations.
Run original20 legacy groups: P/F must retain the intentional failure of
invalid_encoding_and_out_of_range_fail_closed (SET 01000000 is now legal);
compact10 retains invalid_length_never_releases_engine. Check the previously
masked out-of-range assertion separately. P also intentionally changes DRIVE|1
from rejection to a four-edge post-delay; all other malformed-phase cases remain
required rejections. Retain original failure logs, do not relabel them passes.
Run held mode0/2 compatibility checks and retain previous SPI gates.

Formal: prove12/180s for instruction rules, compact refinement outside the
new allocations, and actual public-loaded symbolic-byte mode1/3 programs.
Instruction controls/covers are bounded80/180s; program negatives bounded128/180s.
Validate counterexamples for wrong countdown/update timing and missing input hold.
Finite instrumented preflights must check serialized words and the pin oracle
before program proof. Reset/loading/state invariants are asserted, not assumed.
One attempt per frozen source/task; retain failures and timeouts, no expanded
budget to obtain a pass. Corrected source/harness revisions remain distinct.

Each simulator and synthesis job has a600s limit. Compare whole-chip primitive
cells and state bits using identical locked Yosys commands, including top,
loader, storage, synchronization and executor. Reject latches/check errors.
Record source hashes, commands, wall times, JUnit counts and explicit outcomes.

## Decision

A P/F candidate advances only when its required qualification passes and both
generic cells and state bits are strictly below matched compact10. Choose fewer
cells, then fewer state bits, then P on an exact tie. Otherwise report no clear
winner. This selects an experimental candidate for later physical evaluation,
not production promotion, CMOS5L area/timing, Fmax, silicon or owner fluency.
Instruction packing and seven-word mode1 optimization remain outside this slice.
