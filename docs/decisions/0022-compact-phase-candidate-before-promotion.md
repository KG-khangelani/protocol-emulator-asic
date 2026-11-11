# D22 - Prefer compact phase instructions for the next qualification step

Date: 2026-11-03. Status: selected isolated candidate; production unchanged.

SPI mode 0 separates changing outgoing data from observing incoming data. The
existing coupled instruction samples too early for E0020's declared late target.
Keeping it is still a zero-RTL option under an explicitly faster response bound.
E0020's counterexample remains FAIL; it is not a proof every eight-word program
is impossible or every useful SPI target needs an extension.

E0021 implements and compares two reusable phase operations in isolated copies.
Compact DRIVE combines preparing one TX bit with a masked auxiliary GPIO update;
SAMPLE can wait an explicit accepted-edge count before capturing synchronized
RX. That expresses the seed in eight actual words through the original loader.
The alternative retains explicit SET/WAIT instructions and adds two program
words plus a real banked loader to address them. Both retain 403 execution edges
and capture the intended rising-edge byte at edge 379. The contract is
[`spi-phase-comparison.md`](../specs/spi-phase-comparison.md).

Under identical complete-chip generic Yosys synthesis:

| Option | Used/store words | Generic cells | State bits | Legacy suite |
|---|---:|---:|---:|---|
| Coupled, faster target only | 8/8 | 2,793 | 410 | 17/17 PASS |
| Compact phased | 8/8 | 3,107 (+314) | 412 (+2) | 17/17 PASS |
| Plain phased, banked loader | 10/10 | 3,403 (+610) | 477 (+67) | 16/17 PASS; one declared failure |

Compact saves 296 generic cells and 65 state bits versus this banked candidate.
The latter's +67 bits include 64 extra program bits, a bank bit and two phase
flags. Its original length-nine rejection test fails because nine is now valid;
register 5 also becomes bank control. Compact preserves existing legal-program
and loader behavior, while intentionally allocating previously invalid words.
Neither implementation establishes a minimum encoding or minimum state count.

Select compact for the next **formal qualification experiment**, without copying
it into production `src/`. It meets the wider tested response envelope at lower
generic cost and retains the existing loader. Retain the banked alternative as
a measured capacity/compatibility tradeoff; do not expand storage solely to fit
this byte seed. The faster-target option remains appropriate when its stronger
external timing assumption is explicitly accepted and independently validated.

Before production promotion, prove phase sequencing, exact pending-sample delay
(including counter boundaries), result commit only on valid eighth SAMPLE,
reset/enable/loader abort and refinement of all previous legal operations.
Attempt adversarial instruction/pin permutations and retain counterexamples.
The old production formal proofs do not prove the experimental extension.
All-four-mode/continuous SPI, real-device electrical timing, CMOS5L area/slack,
Fmax and silicon remain unqualified. Generic cell counts are not mapped area.

PR11 remains draft/unmerged. PR8 and compiler work stay deferred. Owner M0
fluency remains PENDING; engineering evidence does not promote learning.
