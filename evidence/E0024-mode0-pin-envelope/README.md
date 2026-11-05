# E0024 - Compact mode-0 external-pin envelope

Observed: 2026-11-03, KhanCreate Windows, existing locked Linux workbench.
Baseline: PR11 `0b0409ea4078a997a0a487f36ebfac286d5d46a7`.
**Full-program pin simulation PASS; input-transport proof PASS;
full-program formal INCONCLUSIVE.** Candidate/production RTL are unchanged.

A matching received byte can hide a timing error, especially when consecutive
bits have the same value. This experiment checks clock, chip select, pin
ownership, rising-edge wire words and result visibility as well as byte values.
It also separates the program's complete pin simulation from the smaller
synchronizer proof. Successful pieces do not convert a timed-out full-chip
proof into a pass.

## Contract, model and useful timing

[The pin contract](../../docs/specs/spi-mode0-pin-qualification.md) and
[D25](../../docs/decisions/0025-mode0-pin-envelope-before-promotion.md) freeze
the assumptions. `pin_timing.py` imports no VM, instruction encoder or RTL.
Expected GPIO and edge lists use pin mathematics; a separate reference test
cross-checks the hand-authored eight-word image against the existing encoding.
Every simulator transaction resets, publicly loads/reads back all32 image
bytes, commits length8, writes TX and flushes the actual synchronizer twice.
The target is detached during loading/readback. Successful transactions have
continuous enable and no reset/reload; reset/disable controls are rejected.

At the20ns simulation clock target, bitj's low/DRIVE edge is2+50j, SCK rises
at27+50j and capture is29+50j. The two-stage synchronizer consumed at capture
therefore represents raw MISO at the rise. MOSI changes only at low boundaries;
high/low intervals, MOSI setup, CS setup and final-rising CS hold are25 clocks.
Last rising377, capture379, CS release/falling402 and HALT403 atPC7 are distinct
events. Raw-valid at379 does not alone accept the transaction; the checker also
requires the complete expected pin trace, declared envelope, wire/data match
and known-image HALT. There is no new RTL acceptance flag.

Two envelopes remain separate:

- **Original seed:** per-bit response requests5..480ns after the low boundary,
  at least20ns input setup before SCK rises, and hold until the next launch.
- **Ideal digital stress:** intended MISO on the closed R+-1ps window, with
  transitions/noise outside it. A requested raw transition exactly on a core
  edge moves1ps before that edge. Exact actual event times are retained.

The1ps values define deterministic test ordering. Ideal flip-flops have no
metastability or electrical aperture in this model. They establish no physical
setup/hold limit, clock jitter tolerance, propagation delay or contention safety.
The50MHz/1MHz values are targets in simulation, not measured silicon timing.

## Final frozen observations

Run: `build/spi-mode0-pins/final02/`. Both simulators pass four groups with
**856 positive transactions and8 negative controls each**. Their complete
public case manifests and representative full traces are byte-identical.

| Cases per simulator | Scope/result |
|---:|---|
|512| All RX bytes, complementary TX, both orders, latest1ps digital setup: PASS |
|256| All96 original quarter-clock response positions in both orders plus64 independently varied per-bit response cases: PASS |
|88| Outside-window noise and offsets around quarter/core-clock boundaries, both orders: PASS |
|2| Early-SAMPLE firmware receives D3/B4 rather than wire69, with correct SCK/CS: retained expected mismatch |
|4| Late declared profiles, including unchanged FF masking: rejected |
|2| One disabled edge or reset: fixed-rate transaction not accepted |

Every positive execution checks all403 public GPIO edges, MISO release,
independent actual SCK rising-edge MOSI/MISO decoding, immediate raw result and
valid at379, no earlier valid at378, and final status. Original response phases
and noise cases supplement the byte alphabet; these are finite selected cases,
not exhaustive independent TX/RX pair or continuous-time simulation.

The firmware control changes SAMPLE delay1 to0 and adds one WAIT edge after it.
Clock/CS timing remains identical, but it consumes raw R-1 instead of R. With
late input, wire69 becomes rawD3 LSB-first or B4 MSB-first; raw-valid also arrives
at378. This is a deliberately wrong program, not a defect in candidate RTL.
For a target launching after R, the unchanged candidate correctly captures
the word actually present on the wire, while the intended-byte/envelope claim
is rejected. Those are different observations and remain labelled separately.

The formal job contains the **actual unmodified input synchronizer and an
independent schedule/observation monitor**, without an executor or loader.
RX/order are symbolic constants. MISO is constrained only to the intended bit
at R=27+50j; all other sampled ticks are arbitrary. Reset comes from the initial
schedule edge. Full-width two-stage recurrence, capture at C=R+2 and the monitor
byte are written assertions. There is no fairness or wall-clock liveness claim.

| Formal task | Mode/depth | Actual result |
|---|---|---|
| Transport rules | prove/8 | PASS; induction step5, base0..7 |
| Reachability | cover/404 | All3 reached: changed outside-window input29; complete69 in each order381 |
| Early C=R+1 monitor | BMC/32 | Expected FAIL at29; consumes raw26 at capture28 instead of intended raw27 |

That induction proves the written transport rules beyond its base prefix. It
does not prove the eight-word instruction schedule, loader or complete SPI
program. E0022/E0023 retain their separate core/integration proof boundaries.

## Failed and inconclusive attempts

[failures/](failures/) preserves these outcomes without rewriting them:

- The actual uninstrumented compact top and public loader were tried through
 444 SAT steps with symbolic TX/RX/order and MISO constrained at the rises.
  Initial attempts failed on this Yosys version's assertion-cell conversion.
  After standard single-clock lowering, direct and Boolean-reduced attempts
  both timed out at the90-second solver limit. Their models had respectively
  19,813,492/14,438,890 variables and54,683,914/38,064,160 clauses. These are
  proof-model costs, not chip area. Neither attempt supplies a pass or a
  reachable candidate counterexample. Full exact logs are losslessly gzipped,
  with readable excerpts, commands, inputs and original SHA256 values.
- Initial transport induction is UNKNOWN despite base0..7 passing. Its
  induction history starts near cycle373 with inconsistent already-observed
  bits. Partial-byte invariants were added as assertions, not input assumptions.
  Candidate RTL and the formal timing assumption were unchanged.
- An all-ones control first FAILS the acceptance check: declared late response,
  no wire transition, raw/wireFF and incorrectly accepted=true. The guard now
  checks declared response deadlines independently of actual window values.
  Failed source snapshots, public trace, JUnit and log remain. That selected
  probe intentionally filtered three other groups; their skips are not passes.

E0023's earlier300-second guided-abort timeout remains unchanged and
inconclusive. The default new CI step runs transport formal and pin simulation;
it does not repeat or relabel the known full-chip SAT timeouts.

## Reproduce and inspect

Inside `protocol-emulator-asic-workbench:2026-07-29`:

```sh
python3 experiments/spi_phase/run_pin_qualification.py
```

Doctor, `make check` (41 reference/provenance cases) and atlas export consistency
pass. No local image build/pull, new dependency, physical run or storage cleanup
was needed. Fresh exact-head hosted results and independent artifact audit
references are tracked on draft PR11.

[result.json](result.json) records scope, all protected/candidate/input hashes,
outcomes, controls and curated-file checksums. [run-result.json](run-result.json)
retains exact commands and generated-source/record hashes. [inputs/](inputs/),
[configs/](configs/), [logs/](logs/), [statuses/](statuses/) and
[simulation/](simulation/) contain frozen sources, results, both JUnit files and
the identical864-case manifest. [public-traces/](public-traces/) retains full
input event lists and selected public edge rows around low/rise/capture/fall
and errors, with full raw JSON hashes. Full403-row traces remain in build/CI.
[witnesses/](witnesses/) selects root signals at every SMT step, with raw VCD
hashes; [counterexamples/](counterexamples/) retains the exact early-monitor
Yosys witness, constraints and generated testbench. These formal step numbers
are not measured nanoseconds. Normalized logs change LF/trailing whitespace
only; compressed failure logs decompress to exact original bytes.

Next: develop measured per-loop invariants/decomposition for the actual
eight-word full-program proof before considering production promotion.
PR11 remains draft/unmerged, PR8/compiler deferred, owner M0 fluency PENDING
and H1-H4 unproven. No full-mode SPI, physical implementation, Fmax, silicon
or production-readiness claim follows.
