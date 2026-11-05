# E0023 - Actual public loader, capture and abort integration

Observed: 2026-11-03, KhanCreate Windows, existing locked Linux workbench.
Baseline: PR11 `284c9cc6e6f6b5b70403a3ab2b704205eac3b861`.
Rung: **experimental integrated digital model**, candidate/production unchanged.

The earlier executor proof checked how one part computes a byte. This slice
checks the connected chip: can its public loader put that program in memory,
can the result registers capture the byte, and what survives an interruption?
Induction checks written safety beyond a finite prefix. Bounded public-pin
witnesses check a particular loaded program. Covers demonstrate reachable
examples; deliberately wrong claims and broken connections test detection.

## Boundary and lifetimes

The [contract](../../docs/specs/spi-phase-integration.md) and
[D24](../../docs/decisions/0024-compact-public-integration.md) define the scope.
Use the actual compact-copy top, eight-word/256-bit program store, data store,
two-stage synchronizer and executor. Read-only formal taps have checked inverse
transforms; the phase observer binds the actual connected executor. There is
no abstract fetch, forced ready, direct preload or result-store replacement.
Uninstrumented public-pin simulation uses the same runtime candidate as E0021.

Universal safety assumes **only chip reset on the first sampled edge**.
Subsequent public inputs, enable and reset vary freely; no fairness, valid
program or stable input is assumed. A symbolic watched address checks all32
program bytes against public writes. Assertions cover length/ready/fetch,
readback, both synchronizer stages, data-register priority, same-edge capture,
phase completion, public ownership and effective engine reset regardless of
enable. Existing top-level FORMAL assertions remain active.

The existing lifetimes matter to future firmware:

- Loader entry resets execution and blocks a simultaneous new capture, even
  with enable0. It retains an older completed RX byte and valid flag.
- TX/alternate payload writes clear valid while retaining raw RX.
- Chip reset clears program, data and engine state regardless of enable.
- A selected loader read still drives all eight public uio pins during reset.
  Selecting runtime exposes the cleared engine GPIO. This is digital mux
  ownership, without an electrical contention or asynchronous CDC claim.

These behaviors agree with the existing K-SHIFT/loader contracts. No candidate
defect requiring a hardware change was found.

## Frozen local results

Final run: `build/spi-phase-integration/final/` using SymbiYosys/Z3 4.15.5.

| Job | Mode/depth | Actual result |
|---|---|---|
| Actual integrated safety | prove/8 | PASS; induction step5, base steps0..7 |
| Public-loaded completion | BMC/80 | PASS; assertions checked through79 |
| Final-capture-edge abort | BMC/72 | PASS; assertions checked through71 |
| Completion/lifetime covers | cover/80 | All4 reached at64,67,70,72 |
| Abort covers | cover/72 | All4 reached at63 |
| Wrong loader-clears-valid claim | BMC/80 | Expected **FAIL at67**; old valid remains1 |
| Disconnected data-store capture mutant | BMC/80 | Expected **FAIL at62**; engine completion is lost |
| Icarus public-pin integration | four groups | PASS, no skips |
| Verilator public-pin integration | four groups | PASS, no skips |

The real public loader writes a four-word LOOP(length2,count8), DRIVE,
SAMPLE(delay3), HALT image. Both byte operands and bit order are symbolic in
formal. After sixteen little-endian byte writes, length4 commit and TX write,
two disabled edges flush the actual synchronizer. Captures occur on accepted
edges6+5j; final capture41, HALT42. Expected TX, RX, valid and status follow an
independent schedule and operands. Four covers include completion, retained
valid after loader read, payload invalidation and reset.

Guided formal abort fixes cut41, the final capture edge, with symbolic kind
(loader read, program write, chip reset) and enable0/1. It starts with no older
valid byte and holds execution disabled after the cut. Universal safety permits
abort timing at any clock. Each simulator additionally checks **512 completed
transfers** (all RX bytes, complementary TX, both orders), **480 fresh-result
abort cases** (all40 cuts2..41, three kinds, two enables, both orders), **48
older-result abort cases**, and storage reset/readback ownership. Simulation
reads back the complete loaded image; guided formal relies on the universal
readback scoreboard rather than adding image-read transactions to its schedule.

The two negative jobs remain FAIL. The supervisor requires exactly those
outcomes, assertion failures and concrete witnesses; it rejects timeout,
UNKNOWN, missing status, missing covers, unexpected failure or skipped tests.
The disconnected-store mutant demonstrates end-to-end sensitivity beyond the
executor-only assertions. It is deliberately faulty, not the unchanged candidate.

## Reproduction and retained evidence

Inside `protocol-emulator-asic-workbench:2026-07-29`:

```sh
python3 experiments/spi_phase/run_integration.py --with-simulation
```

No local image build, pull, large physical run or storage cleanup was needed.
Doctor and `make check` pass; the latter runs35 reference/provenance checks.
The CI workflow runs this separate experimental step and uploads raw witnesses.
Fresh exact-head CI and ZIP digest/audit references are tracked on draft PR11.

[result.json](result.json) records scope, protected/candidate/input hashes,
counterexample semantics and curated file checksums. [run-result.json](run-result.json)
contains exact commands, modes/depths, statuses, runtime source hashes and
simulation counts. [inputs/](inputs/) retains compiled formal inputs and exact
readout patches encoded in JSON; [configs/](configs/), [logs/](logs/),
[statuses/](statuses/) and [simulation/](simulation/) retain final results.
[witnesses/](witnesses/) selects public/actual-top signals at every SMT step,
with raw VCD hashes. [counterexamples/](counterexamples/) retains exact Yosys
witness, SMT constraints and generated testbench for both negative jobs. Bulk
SMT models, compiled simulators and full VCDs remain under build/CI. Log
normalization changes LF/trailing whitespace only; original hashes remain.

Initial failures remain inspectable under [failures/](failures/):

- The wider guided symbolic abort cut2..41 exceeded300 seconds (exit124,
  statusMISSING) while checking step40. This is no pass through40 and no
  counterexample. Preserve its exact compiled inputs, configuration and log;
  the final guided formal cut is narrower and explicitly declared.
- The first simulation fixture failed4/4 because a runtime-read helper expected
  stable GPIO while the pins still selected loader TX-write mode. Moving the
  observation after runtime selection/flush fixes the fixture. The failed
  JUnit retains actual values/stacks; that initial test-source version was not
  archived. Candidate/production were not changed by this correction.

## Limits and next action

This is written integrated digital safety plus finite public-loaded kernel
qualification. Induction is not arbitrary-program termination. The guided
abort proof covers its declared final edge, and simulation of all cuts is not
an exhaustive proof for every byte at every cut. No fairness or eventual
enable is promised. No full SPI transaction/mode, physical input timing,
metastability, CMOS5L area/slack, Fmax or silicon result follows.

Next: qualify the eight-word mode-0 program end to end under explicit external
pin timing assumptions. Keep production RTL unchanged, PR11 draft/unmerged,
PR8/compiler deferred, H1-H4 unproven and owner M0 fluency PENDING.
