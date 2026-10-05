# E0019 - Bounded host service before buffering

Base main: `155e130ea402f78a86558fb3c2b094c536be41a4` (PR7).
Contract: `docs/specs/p-uart-rx-host-service.md`; decision D19. No production
RTL, firmware, official ports/source list, config or 6x4 allocation changes.

The explicit workload preserves two bytes externally: first raw byte is ONLY
tentative; known-image a7/raw-valid and a later terminal read accept both
atomically. Any framing FAULT/control interruption rejects the tentative pair.
Input source owns released RX1; loader requires quiescence as in E0018. Hold
ena/rst_n high, ui7 low and execution unpaused through acceptance. This is a
settled integer-edge host reference, not an OS driver or physical access proof.

## Independent expectations and focused falsification

`tools/uart_rx_host_service.py` consumes only scheduled public observations.
Register-lifetime expectations come from frame/schedule mathematics, not
`Machine.edge`. First capture C1 and overwrite C2 differ by 10P. Worst poll
delay is H-1; H+L<=10P puts the copy at most C2-1. Formula/bit-rate/clock
durations are DERIVED at the 50 MHz target, not physical measurements.

Three reference groups enumerate every P4 boundary H/L/poll residue (780
cases), check P434 and maximum legal period algebraically, quarantine/discard
and postacceptance retention, and the many-to-one overwrite observation.
`make check` runs these alongside all existing model/provenance checks.

Three public-pin cocotb groups check P434 quarter-phase corners at H4338/L2,
P4 last-safe and H1/L1 coincident poll/copy, first/second bad stop after tentative
capture, disable/reset/reload without cache leakage, and two different first
bytes with the same second byte. All observer selector settles are budgeted
inside exact 20,000ps execution/terminal clocks. Diagnostic reads are NOT fed
to the host reference. Focused Icarus and the coherent dual-simulator/clean CI
ladder pass as recorded below; final-record exact-head CI remains separate.

The unsafe P4 H39/L2 example polls before capture and at edge79, then copies
on overwrite edge81. For first 5a or 96, second a5, the late reader sees the
same raw a5/valid1; terminal a7/a5/valid1 has no chip error flag. This deliberately
inadmissible observer is separate from HostReader, whose constructor rejects
H+L>10P. No stored-register reader can recover the overwritten first byte.

`formal/uart_rx_host_deadline.smt2` plus `tools/check_host_deadline.py` checks
the integer safety negation is UNSAT and the one-edge weakened bound is SAT
(example P4,H1,L40,d0). It is not an integrated RTL liveness/physical-host
proof. Existing ten RTL proof/cover/mutation statuses remain required by
`make formal`; the new lemma does not replace them.

## Accounting and limits

Zero new chip storage/cells are expected because production RTL is unchanged;
the coherent generic screen must confirm the prior 2,793 cells/410 state bits.
Eight 32-bit program words are unchanged. External two-byte cache and host
control/service state are outside CHIP_COMPLETE and must not be hidden in a
complete-system comparison. This workload is possible without a buffer; no
buffer RTL is justified or implemented. If physical host service cannot meet
H/L, queue capacity, read/ack, overwrite/error and abort semantics need a new
contract before adding storage.

Autonomous/unserviced two-byte retention, continuous/full-duplex RX, general
async service, analog baud tolerance, metastability, CMOS5L, gate-netlist timing
and silicon remain NOT_EVALUATED. M0 owner fluency remains PENDING; engineering
progress does not promote human understanding. No physical rerun occurs.

## Coherent local qualification

`make check evidence` passes at frozen working-tree collector
`20261005T092252111242Z`; `local-check-evidence.log` records all 28 reference/
model/provenance groups and the eleven collector stages. Both simulators pass
all 20 regression groups, including the three added host groups. All ten required
RTL formal outcomes match, including expected mutant `FAIL 0 2` (wrong WAIT
decrement rejected); the nine proof/cover statuses and integer host checks pass.
Engine proof takes
187s process time. Independent re-review is clean (`review.md`).

`local-manifest.json` SHA-256:
`fdd0cc97ed892511fc012d165f5a1943a9e774dc82e44c753b1e12ef45592cc3`.
All 31 run artifact hashes and all 136 then-current source hashes were verified
before recording this result. The manifest honestly records dirty source at
base main, not a clean committed checkout. Post-run qualification prose needs
its own exact-head CI; no source revision is implicitly called green.

An independent netlist recount confirms 2,793 generic leaf cells and 410 state
bits, matching E0018 (+0/+0). Production source hashes are unchanged. Curated
dual-simulator JUnit, waveform provenance and formal-status summary accompany
the manifest; bulk/logs remain under ignored build and future CI artifacts.

The official competition page was rechecked 2026-10-05 and still states the
2027-01-18 deadline, current 6x4 CMOS5L allocation and open-source reprogrammable
protocol objective. [Official source](https://blog.janestreet.com/protocol-emulator-asic-competition/).

## Clean implementation qualification

Implementation head `9379d686fb37f912a4beb874c0f506b2f5d2541f` passes
push test [37290646619](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37290646619),
PR test [37290652951](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37290652951)
and docs [37290646419](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/37290646419).
Downloaded collector `20261005T093737983770Z` records a clean checkout, eleven
passing stages and 20 passing groups per simulator. All 31 ORIGINAL artifact
hashes and 136 source hashes were verified against the clean committed local
files before this record update. Independent CI-netlist recount reproduces
2,793 cells/410 state bits; no production RTL changed. `ci-manifest.json`,
JUnit reports, formal outcomes and `qualification.json` preserve identities.

Curated local/CI JUnit copies each add one terminal LF relative to their original
artifact; they are content-equivalent, NOT byte-identical to the manifest's
original JUnit hashes. `qualification.json` records original and curated sizes/
hashes explicitly. Both curated manifest copies preserve exact original bytes.
All 31 audits refer to ORIGINAL collector files, not normalized curated copies.
The GitHub-reported ZIP digest is recorded, not independently checked. Bulk
is ignored under build; the artifact expires 2027-01-03. Curated evidence persists.

Independent implementation/evidence review is clean. The final documentation
record requires its own exact-head CI before normal merge. [PR8](https://github.com/KG-khangelani/protocol-emulator-asic/pull/8)
tracks final reviewed head, checks, normal merge and post-merge CI separately;
no future/inferred merge result is marked PASS here. M0 fluency remains PENDING.
