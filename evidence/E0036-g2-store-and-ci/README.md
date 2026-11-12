# E0036 - G2 current-revision audit and remaining qualification gates

Checkpoint 2026-11-12. **The clean G2 CI audit, complete program-store proofs
and exact physical-test selection pass. literal255 fails placement capacity;
od128 physical qualification remains in progress. Production is unchanged.**

GitHub [run43213815994](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43213815994)
at `31ebf8247fab05f2e6e23bc94e1d861562f0f1b5` passes all three original G2 gates.
The independently downloaded archives match GitHub's SHA-256 digests.
[Verification](ci/verification.json) checks the exact candidate source files
against E0035's current manifest, protocol inputs against their committed Git
blobs, results, both simulators' records and the existing compact10 SPI reference.

- Both od128 and literal255 pass the **full** I2C matrix in Icarus and Verilator:
  1,160 identical records each, comprising 996 OK, six NACK, 152 bounded timeout
  outcomes and six rejected controls. This closes E0035's missing full literal
  second-simulator run without rewriting that earlier failed launch.
- Both candidates pass the real-store/instruction boundaries and scoped
  instruction proofs; generic complete-chip cost is unchanged.
- od128 passes 36 abort/reload records and the twelve legacy public groups
  in both simulators. All 1,052 SPI records equal the retained compact10
  expectations, including four expected input-hold failures.

The archives are identified in [artifact metadata](ci/artifacts.json).
Curated execution logs, result summaries, JUnit files and all public records
are retained here. `witnesses.tar.gz` archives preserve all 1,748 original
JSON witnesses byte for byte, with deterministic archive timestamps.
They are simulator/oracle observations, not physical measurements.

After downloading the three original ZIPs to `build/g2-ci-31ebf82/` and
extracting each into a directory named by its artifact ID, run
`python evidence/E0036-g2-store-and-ci/ci/verify_ci.py` to reproduce the audit.
The verifier reads protocol input bytes from the immutable source commit;
later workspace changes cannot silently substitute new inputs.

The [frozen physical qualification](../../docs/specs/g2-cmos5l-qualification.md)
uses a separate manual `gds-g2` workflow and the unchanged G1 physical lock.
Its new acceptance checker rejects missing/skipped groups, missing or changed
records, false netlist labels and mismatched submitted/tested bytes. Eight
checker test groups pass. Local non-staging preparation regenerates the exact
E0035 od128 hashes. [Run43221121151](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43221121151)
at e2ff52e passes all four G2 jobs, including the exact eighteen-group selection
in both simulators. Its downloaded archive digest and source identities pass;
all 1,052 SPI, 1,160 I2C, four boundary summaries and 36 abort/reload records
match the frozen expectations. [Selection audit](physical-selection-ci/verification.json)
retains the original records and witnesses. The first local selection attempt
remains interrupted by Docker's `unexpected EOF` at 12:26:17 UTC.

## Complete actual-store proof

[Store verification](store/verification.json) audits **652 od128 assertions and
1,287 literal255 assertions**. Every allocated word's transition and read
relation, plus all common bank/length/ready/valid controls, pass unbounded
k-induction. The 33/65 positive tasks include one three-target reachability
task per candidate. Positive models keep all actual storage/control logic,
have no reset/environment assumptions and do not initialize actual program
bits. Partitioning removes only other assertions, without assuming lemmas.

Two reset-reachable od128 mutations fail at inspected wrong writes: bank 8
aliases word 68 to word 4, and a byte-lane swap writes the wrong eight bits of
word 2. Nine corrupted proof-summary controls are rejected by the independent
auditor. These checker controls add no RTL coverage. Two archives retain 433
exact proof inputs, lowered models, configurations, logs, statuses and VCD
witnesses. Reproduce the audit without rerunning the solvers:

```sh
python evidence/E0036-g2-store-and-ci/store/verify.py --output build/g2-store-replay
```

The original combined run `i2c-store-local-06` remains `NOT_QUALIFIED`: its
first alias counterexample used arbitrary pre-reset data and did not meet the
required reachable-write check. Corrected controls in `i2c-store-local-07`
guard only negative read assertions until after reset. The auditor verifies
the exact corrected mutant bytes and reuses unchanged, successful positive
proofs. It does not turn the original failed aggregate into a pass. A separate
CI store gate runs the corrected complete proof, both audits and all nine
checker controls from scratch.

That clean run now passes: [run43229238795](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43229238795)
at d3c340f completes **all five gates**, including all 100 store tasks and both
store audits in one successful aggregate. [Downloaded-evidence audit](ci-d3/verification.json)
checks every named archive digest, generated source bytes, full protocol and
selection records, immutable protocol inputs, and replays the store auditor
against the actual CI models/configurations/logs/witnesses. All nine corrupted
summary controls are rejected. The original store ZIP is retained byte for
byte as `ci-d3/store-original.zip`; other unchanged protocol witnesses already
have durable copies in this evidence record. The compressed verification
runner reproduces the five-archive audit after extracting it into `build/` and
downloading/extracting the identified ZIPs into `build/g2-ci-d3c340f/`.

Earlier whole-memory timeouts, superseded partial runs and interrupted SAT
attempts remain in `development/`. The large SAT attempt had the same Docker
connection error; its cause was not established. None is a successful proof.

## First physical comparison

Both manual runs use e2ff52e, the exact E0035 source hashes and unchanged pinned
8x4 conditions. [literal255/run43224856998](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43224856998)
**fails placement capacity**: mapped cell area is 1,281,967.344 square
micrometres / 96,220 instances; placement's pin-density-adjusted utilization
is 111.564%. `GPL-0301` stops before routing. Precheck and netlist jobs are
skipped. [Failure evidence](physical/literal255/result.json) verifies both
original archive digests, source bytes and resolved fixed conditions, and
retains mapping/placement metrics and full logs. This rejects the measured
implementation; it provides no routed comparison or timing qualification.

[od128/run43224847282](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43224847282)
**fails global routing** with `GRT-0228`: horizontal edge usage 1,717 exceeds
the router's internal limit of 1,700 at (92, 97). This is not an estimate that
the chip needs only one percent improvement. Mapping produced 39,806 cells /
564,744.3984 square micrometres, including 4,278 sequential cells. Placement
completed; there is no final routed timing/area result, precheck or netlist pass.
[Failure evidence](physical/od128/result.json) verifies both original ZIPs,
source/configuration identities and actual action/image/compiler observations.
It retains intermediate metrics and complete failure logs; temporary URL query
strings are redacted with original/retained hashes recorded.

`tools/audit_g2_physical.py` now binds completed physical jobs, original archive
digests, source/layout/netlist identity, all routed limits, all ten prechecks,
actual consumer downloads and all eighteen public test groups. Eight focused
test groups replay retained G1 observations and reject corrupted controls.
The real failed od128 run is rejected as `NOT_QUALIFIED`. A complete positive
G2 archive bundle does not yet exist, so its end-to-end acceptance path remains
unexercised. Every gate remains required. G2 stays active through qualification,
integration and publication; G1 and owner-fluency boundaries remain.

## Preparation for production integration

Historical generators now read the five explicitly archived E0020 source files
in `experiments/spi_phase/baseline/`. Every build verifies them against E0020's
original hashes and source commit. Experimental input manifests name these
actual inputs; the ordinary production source list remains unchanged.

[Baseline verification](frozen-baseline/verification.json) regenerates all three
phase variants, four timed variants, both G2 candidates and the legacy formal
inputs while an active file-open guard forbids reading production `src/`.
All generated chip hashes match the earlier builders/results. An altered
archived store is rejected. The first verification script incorrectly compared
the old banked phase design with compact10; that reference mistake is retained,
then corrected by checking the exact prior builder at d3c340f. No RTL change or
fresh protocol qualification follows from moving the historical inputs.

## Bounded memory-write simplification screen

An isolated rewrite spells each byte write as four constant lane assignments.
The other four chip files, capacities and interface remain byte-identical.
[Screen evidence](lane-screen/verification.json) records these generic results:

| Candidate | Original primitive cells | Explicit lanes | State bits |
|---|---:|---:|---:|
| od128 | 27,065 | 24,391 | 4,278, unchanged |
| literal255 | 51,723 | 46,390 | 8,343, unchanged |

od128's complete store equivalence passes in 124.001 seconds from corresponding
state, which reset establishes. literal255's comparison times out at 240.021
seconds and remains inconclusive. A separate local SAT theorem proves the byte
replacement for all word/data/lane values; a wrong-lane control produces an
inspected differing write. The first control parser failed on escaped VCD
names; its inputs/logs/witness remain retained alongside the corrected audit.

This is roughly 10% less generic logic, **not a mapped or routed saving**.
The original od128 routing failure now warrants qualifying this rewrite as a
separate candidate, followed by a matched physical trial. It has not been
adopted into production. The failed physical runs retain original E0035 bytes.
