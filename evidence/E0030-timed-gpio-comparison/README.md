# E0030 - Eight-word phase1 SPI through timed GPIO

Observed 2026-11-12; implementation 19265ffb711c2db5d4fe4946355c4afbe2ed929f.
**Select isolated P for the next mapped comparison.** It expresses both modes1/3
in eight words, preserves the ten-word external timing, and saves 443 generic
cells (12.34%) and 65 state bits
(13.63%) against the matched compact10 design.

| Design | Primitive cells | State bits | Phase1 words |
|---|---:|---:|---:|
| compact8 | 3,107 | 412 | does not fit this template |
| compact10 | 3,589 | 477 | 10 |
| P | 3,146 | 412 | 8 |
| F | 3,228 | 429 | 8 |

These are identical-command, complete-chip generic Yosys counts, including
top, loader, program/data storage, synchronization and executor. They are not
CMOS5L area, placement, timing or Fmax. The matched compact10 uses the compact
engine with the banked ten-word top/store. E0021's older plain-phase banked
implementation is a different baseline.

## Mechanism and timing

P adds SET post-delay 0..63 in [29:24] and DRIVE post-delay 4*k in [2:0].
It reuses the existing counter/state: +39 cells and no new state bits against
compact8. F adds SET pre/post delay 0..31 and latches final GPIO/direction before
a deferred update, costing 17 additional state bits.

Both use explicit idle SET, CS-low/post23, LOOP3x8, DRIVE, trailing SET,
SAMPLE23, CS release, HALT. P waits 24 after DRIVE; F waits 24 before trailing SET.
CS asserts at 2, leading clocks 27+50*j, wire samples 52+50*j, captures 76+50*j,
release 427, HALT 428. The independent oracle and HELD_RESPONSE premise are unchanged.
New encodings deliberately allocate formerly-invalid words; the D30 high-bit
description is corrected in a dated note.

## Qualification

- Each P/F reference sweep passes 3,072 paired-byte transactions across modes1/3,
  both orders and early/late/mixed response profiles. TX=(73*RX+19) modulo256;
  these finite sweeps are not all65,536 TX/RX pairs.
- Each of compact10/P/F on each simulator passes 1,036 phase1 positives and 12
  held mode0/2 positives. Four edge-only input controls fail with the expected
  received-byte error. All 1,052 transfer records per run are retained.
- Complete records match between simulators for each variant. Pins, direction,
  receive byte/valid and terminal timing match across variants; intermediate
  RUN/WAIT state is intentionally excluded from that cross-variant comparison.
- General instruction tests exercise every encoded delay, four value/direction
  masks, loop completion, instruction changes while waiting, pauses, reset,
  final pending edges, loader abort and remaining invalid encodings.
- The original 20 legacy groups remain unchanged: compact8 passes 20; compact10,
  P and F each retain 19 passes and one declared failure. Compact10 accepts length 9;
  P/F accept timed SET 01000000. The previously masked out-of-range check is run
  separately. P also deliberately accepts DRIVE|1 as post-delay 4.
- P/F instruction rules pass prove 12/180s. P/F actual public-loaded mode1/3
  programs pass induction with symbolic TX/RX, order and clock polarity,
  plus 12 finite instrumented preflights each. GPIO/byte/loader/state invariants
  are asserted, not assumed.
- Four instruction negative controls and four actual-program negative controls
  yield validated counterexamples. Missing input hold still breaks the byte.
  The instruction cover sets reach 4 P and 5 F obligations within depth 80.

## Retained inconclusive attempts

The first hierarchical compact-refinement attempt times out at 180s for both
variants. A distinct flattened/cleaned solver representation uses byte-identical
generated obligations, the same assumptions, depth 12 and 180s budget. P passes
in 161.366s; F times out again. No timeout is reported as a pass. The whole-program
proof and instruction-rule passes do not substitute for F's missing refinement.

Local candidate qualification is P=PASS, F=INCONCLUSIVE_REFINEMENT_TIMEOUT.
The selection rule applies per candidate; F does not advance. No budgets were
expanded, and there is one attempt per retained configuration. Clean CI results
are recorded separately and may resolve an inconclusive local attempt.

## Reproduction and retained records

Run the locked workbench with:
```text
python3 experiments/spi_phase/qualify_timed_gpio.py --output build/timed-gpio/fresh
```
The runner requires a new output directory and records each bounded attempt.
[result.json](result.json) joins the seven gate records. comparison/ retains the
four generated sources/patches, synthesis logs, original legacy failures,
JUnit records and public traces. instruction_*, refinement_* and program_*
retain generated readouts, exact proof configurations, logs and witnesses.
Raw patches/logs/VCD/record streams are losslessly gzip-compressed; SHA256SUMS covers
the curated files. The initial finite preflight and smoke summaries are retained
under preliminaries/. The separate existing SPI gate is verified in
[prior-spi-verification.json](prior-spi-verification.json).

Production src/ and the historical compact builder remain byte-identical.
No physical/production promotion, arbitrary-program termination, electrical
aperture, full protocol compliance, minimum-state or owner-fluency claim follows.
Next compare P and compact10 under the same mapped CMOS5L conditions.

## Clean implementation verification

Commit19265ff passes the clean timed comparison in
[run43148870589](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43148870589).
All recorded input hashes match the commit's Git blobs. All six public record
sets and corner traces, all generic measurements and all generated formal
inputs match the local run. The downloaded artifact digest and curated
checksums are verified in [remote-qualification.json](remote-qualification.json).

Both candidates qualify on the clean runner. Flattened refinement takes13.195s
for P and20.263s for F; the hierarchical checks also pass. The three local
timeouts remain inconclusive historical attempts. P is still selected on cost:
82 fewer cells and17 fewer state bits than F. The clean proof result records,
configurations and logs are retained under clean-ci/. The separate previous
SPI gates also pass with source identities verified. No additional solver
budget or weaker property was used.

## Published research snapshot

[v0.1.0-alpha.4](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.4)
publishes source d707ee5. The publication runner independently passes the locked
ladder and all five SPI gates. All 15 published asset checksums, every recorded
input source hash, the registry manifest/config digest and image source revision
are verified. Anonymous package access succeeds. Publication-run public records
and whole-chip costs match the local evidence; both candidates qualify and P wins.

[release-verification.json](release-verification.json) retains the public image
digest and asset identities. [release-workflows.json](release-workflows.json)
records the successful tag publication, timed comparison, earlier SPI gates,
full regression, docs and atlas checks, plus the documentation commit's main
checks. The release tag's full regression is run43150438747. The earlier
implementation's five green workflows are in
[implementation-ci.json](implementation-ci.json).
