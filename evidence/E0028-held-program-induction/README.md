# E0028 - Held-response eight-word SPI program proof

Observed 2026-11-11 UTC / 2026-11-12 Johannesburg, baseline 3927165.
**The actual public-loaded HELD mode0/2 programs now pass k-induction under
their written input-hold premise.** Production and compact candidate RTL are
unchanged. This closes the delayed-program proof gap left explicitly by E0027.

## Results

| Check | Result |
|---|---|
| Actual-program induction, configured depth12 / 180s | PASS, successful induction step9, 40.136s locally |
| Symbolic scope | Both CPOL values (modes0/2), both orders, all TX/RX byte pairs |
| Wrong public MOSI goal, BMC44 / 180s | Expected reachable FAIL; checked first-drive witness, 25.079s |
| Missing first post-sample hold, BMC92 / 180s | Expected reachable FAIL; checked wire/consumed-bit witness, 51.209s |
| Finite instrumented preflights | 12 PASS across both modes/orders and early/late/jitter inputs |
| Independent image and pin checks | All serialized words match E0027; all preflight traces pass its oracle |
| Formal terminal reachability cover | NOT_ATTEMPTED; finite terminal witnesses are separate |
| New synthesis/physical/Fmax/silicon | NOT_EVALUATED |

See [run-result.json](run-result.json) for exact hashes, commands, timings and
validated negative observations. Raw logs, statuses and inputs accompany each
formal task; instrumentation patches, counterexamples and finite traces are gzip-compressed without
changing their content. The initial declaration-order preflight compilation
failure is preserved under `initial-preflight-failure/`. It occurred before
any solver attempt and was corrected without altering the formal driver.

## What was proved

The real compact top, public program/data stores, input synchronizer and
executor are compiled together. Read-only taps expose actual state; no DUT
state is preloaded or assumed. The driver serializes32 bytes, commits8 words,
writes symbolic TX, flushes twice and runs404 enabled edges before HALT/reset.
Program bytes, loop/shift state, partial RX, synchronization, public pins,
raw/valid timing, HALT and reset are assertions.

CS asserts at3; bit j launches at3+50j, wire sample S_j=28+50j, trailing edge
T_j=53+50j, actual capture C_j=52+50j. CS release403 and HALT404 retain the
written setup/hold margins. CPOL is established while CS is high.

Raw MISO equals the intended bit at core ticks S_j..T_j. This is a consequence
of HELD_RESPONSE: latest response is launch+24; earliest next response is
after T_j. Other raw ticks and the public raw/valid selector remain arbitrary.
Capture consumes raw C_j-2=S_j+22. This proof covers that delayed program,
not E0025's different edge-only program.

## Why the hold condition matters

The checked negative retains the correct first wire sample at execution28
but removes its subsequent hold band. The solver chooses RX=0x02, LSB-first:
raw MISO is0 at execution28,1 at execution50, and the real synchronizer presents
that1 for capture52. The sampled-input assertion fails at cycle88. Thus a
correct bit at the wire sample alone cannot justify delayed capture.
The counterexample is reachable BMC evidence, not an induction-only failure.

The other control changes only the first-drive MOSI goal. Its trace shows
the actual correct transmitted bit and failure of the deliberately wrong goal.
Neither control changes the DUT or the loaded program.

## Boundaries and next step

The proof is universal over the declared symbolic inputs under this fixed
public loading/execution sequence. It is not an arbitrary-program, arbitrary
pause/abort or all-four-mode result, and it adds no analog qualification.
E0023's separately scoped integration safety and E0027's dual-simulator evidence
remain separate. Earlier covers/timeouts and counterexamples are not reclassified.

Next investigate mode1/3 scheduling in the same eight-word capacity. The
examined ten-word family is not a lower bound. Preserve this fitting program
and its hold condition while measuring any encoding/capacity alternative.
See [D29](../../docs/decisions/0029-held-program-induction.md) and the
[frozen experiment](../../docs/specs/spi-held-program-proof.md).

## Clean remote qualification

Implementation `3254d25abf62b5c5cefb8852eaeb3ae80691d192` passes the expanded
[SPI CI gate](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43120985742).
The earlier program-sensitivity and four-mode screens also pass in that run.
The artifact ZIP matches GitHub's SHA-256; all recorded source hashes match
that exact commit, generated formal inputs match local, and all12 finite
preflight traces are byte-identical. Both negative traces are independently
validated; they need not choose the same symbolic bytes on different runners.
See [remote-qualification.json](remote-qualification.json) and
[remote-run-result.json](remote-run-result.json).

## Published research snapshot

[v0.1.0-alpha.2](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.2)
publishes this milestone. Its publication run43120993964 passes the full locked
ladder and all three focused SPI gates. All six checksummed release assets
match; the public container version resolves to the manifest's exact digest
and its OCI source label matches3254d25. Anonymous registry access passes.
See [release-verification.json](release-verification.json). No full local image
pull was needed for this publication check.
