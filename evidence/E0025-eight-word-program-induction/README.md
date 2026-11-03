# E0025 - Actual eight-word program induction

Observed: 2026-11-03 UTC, KhanCreate Windows, existing locked Linux workbench.
Baseline PR11: `4e207793b6cc7fb6602c4e8ee43775be4e9c28e7`.
Result: **written actual loaded-program properties PROVED by k-induction**.
Candidate and production RTL are unchanged.

The earlier large proof had to rediscover a long sequence of nearly identical
loop stages. Here the proof states what each stage must contain and proves
those facts together with the original public goals. Induction checks that a
correct history preserves the facts into the next step, extending beyond the
finite base prefix. The stage facts are assertions, not assumptions about
how the chip behaves.

## Subject, premises and non-replacement audit

The [frozen contract](../../docs/specs/spi-program-invariant-attempt.md) and
[D26](../../docs/decisions/0026-actual-program-induction-with-proved-invariants.md)
define this one bounded experiment. Preserve E0024's exact driver, eight words,
public byte writes/length commit/TX write/two flush edges, normal403-edge
execution, post-HALT reset and quiescent tail. Both bytes and bit order are
symbolic constants. Raw MISO and raw/valid read selection vary freely each
tick; only MISO at R=27+50j must equal the intended bit. No input assumption
was added or strengthened. Those sampled digital premises do not specify
physical setup/hold, metastability, clock jitter or propagation delay.

The compiled model contains the actual compact top, engine, all256 stored
program bits, program-length/ready, data registers and two-stage synchronizer.
Only read-only output taps and a module rename are added. Their transforms
have checked inverses; removal of the two harness includes recovers the
byte-identical E0024 public driver and its original assertions. There is no
preloaded instruction memory, abstract fetch, forced internal state, assumed
ready/result, new functional input or monitor-only substitute.

[model-audit.json](model-audit.json) independently inspects the generated model:

| Actual module | State bits retained |
|---|---:|
| Executor, including phase flags |110|
| Eight-word program store plus length/ready |261|
| Data registers |25|
| Input synchronizer |16|
| **Actual DUT total** |**412**|

The harness has55 additional proof-only/history bits; they are not a chip cost.
The model contains82 assertions and8 assumptions, all8 from the original
unrolled MISO-at-R site in the public driver. Its symbolic values remain TX8,
RX8, order1, raw MISO1 and read selector1. New loading/per-loop facts appear as
assertions over actual readouts, including the partial received prefix.
No stronger input premise or smaller production counter/store was used.

## One configuration and its result

The fixed budget is one local `prove` job, depth12, Z3,180-second subprocess
wall limit. There was no post-result change of assumptions, depth or budget,
and no adaptive proof retry.

| Evidence | Actual outcome | Interpretation |
|---|---|---|
| Base case | PASS, steps0..11 | Finite initial prefix |
| Induction | PASS at step9; total proof subprocess7.103s | Written properties hold for all sampled steps under the fixed driver/premises |
| Four Icarus preflights | PASS through444 ticks each | Finite actual-program witnesses, not formal reachability covers |
| E0024 direct/reduced444-step SAT attempts | Historical INCONCLUSIVE, unchanged | Their two90-second solver timeouts are not relabelled by this result |

The proven conjunction includes public loading and every stored byte, ready/
length, payload/result lifetimes, each loop's PC/wait/count/phase/shift state,
sampled-bit alignment, exact public GPIO and raw/valid observation, HALT at
execution403/PC7 and subsequent reset. It retains the original result capture
at379 and CS release402. This is not merely a12-step pass, a new444-step BMC,
arbitrary-program termination or unrestricted reset/disable/reload behavior.

The finite preflight derives simulation drivers from the same harness. It
replaces the external formal assumptions with assertions, drives concrete
bytes/orders and checks the actual instrumented top. Cases are TX96/RX69 in
both orders, TX00/RXFF LSB-first and TXFF/RX00 MSB-first. It does not claim
exhaustive simulation or a formal cover. Existing E0024 pin simulations and
their counterexamples remain separate evidence.

## Initial failure and retained records

Initial preflight compilation fails under Icarus strict net typing because
generated assignments/simulation logic precede declarations. Reordering these
generated declarations repairs the harness without changing DUT behavior. No
formal job ran before that correction. Failed compiled inputs, simulation
driver and compiler log remain under [failures/](failures/); the then-runner's
byte snapshot was not archived. All prior timeouts and counterexamples under
E0020-E0024 remain unchanged.

[result.json](result.json) records scope, protected/candidate/input hashes,
budget, proof classification and curated checksums. [run-result.json](run-result.json)
retains exact commands, generated hashes and raw status. [inputs/](inputs/)
contains every compiled source/binding/invariant and JSON-escaped exact readout
patch. [program.sby](program.sby), [program.log](program.log), [status.txt](status.txt)
and [solver/](solver/) retain configuration, base/induction logs and model
generation commands. [preflight/](preflight/) contains all four finite drivers,
clocks and logs; [preflight.json](preflight.json) records their outcomes.
Large generated models remain under build/CI with source hashes. Normalized
logs change LF/trailing whitespace only; original hashes remain inspectable.

Reproduce in `protocol-emulator-asic-workbench:2026-07-29`:

```sh
python3 experiments/spi_phase/run_program_invariants.py --output build/spi-program-invariants/new-attempt
```

Doctor and `make check` (41 reference/provenance cases) pass. Atlas consistency
and fresh exact-head CI/artifact audits are tracked on draft PR11. CI uses the
same configuration/limit and explicitly requires an inductive PASS. No local
image build/pull, dependency installation, physical run or storage cleanup was
needed.

## Limits and next checkpoint

This resolves the written E0024 normal-transaction claim under its original
sampled digital assumptions. It establishes neither completeness of the
properties nor other SPI modes, multi-byte service, electrical/physical timing,
CMOS5L fit, Fmax, silicon, production readiness or H1-H4. No formal reachability
cover or new formal negative-control run was performed in this bounded attempt.

Next: independently examine property/input sensitivity, actual bad-firmware
controls and reachability before production promotion. Keep PR11 draft/unmerged,
PR8/compiler deferred and owner M0 fluency PENDING.
