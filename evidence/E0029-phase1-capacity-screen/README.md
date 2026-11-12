# E0029 - Existing-instruction phase-1 capacity screen

Observed 2026-11-12 UTC / Johannesburg, baseline969323d.
**Mode1 saves one word and reaches nine; mode3 remains at ten in the declared
family. No seven/eight-word candidate passed that bounded screen.** These
positive programs are reference-only: the actual store still holds eight words.
Production and compact candidate RTL are unchanged.

## Results

| Check | Result |
|---|---|
| Four independent boundary/model tests | PASS |
| Timing layouts examined | 60,000; one four-operation timing shape retained |
| Prefixes per GPIO/body variant | 865 |
| Reference schedules assessed | 6,920 across modes1/3 |
| Minimum within declared family | Mode1:9 words; mode3:10 words |
| Best-reference sweep | 3,072 positive paired-byte cases, both orders and three response profiles |
| Edge-only input controls | Four expected received-byte failures |
| Public eight-word deletion controls | 108 expected rejections per simulator |
| Real loader length9/10 commit controls | Four expected rejections per simulator; only32 legal bytes written |
| Icarus / Verilator | PASS; all112 case records and108 full traces byte-identical |
| New formal, synthesis, physical, Fmax or silicon result | NOT_EVALUATED |

| Mode | Words | Candidates | Accepted |
|---|---:|---:|---:|
| 1 | 7 | 4 | 0 |
| 1 | 8 | 208 | 0 |
| 1 | 9 | 816 | 4 |
| 1 | 10 | 2,432 | 12 |
| 3 | 7 | 4 | 0 |
| 3 | 8 | 208 | 0 |
| 3 | 9 | 816 | 0 |
| 3 | 10 | 2,432 | 4 |

The single local search completed in59.614s and the reference sweep in26.559s,
within their separate180s budgets. Both simulator attempts passed within180s;
there were no failed qualification attempts or solver retries in this study.
The original seven four-mode oracle tests and locked workbench Check also pass.

## Why mode1 can save a word

With fixed SCK pull-down, interval [0,1] already supplies one complete low
idle interval. Mode1 may assert CS at execution1, then retain the full25-tick
setup: first leading edge26, first sample51, final sample401, CS release426
and HALT427. Delayed captures are sample+24 and consume raw sample+22.
The previous oracle parameter guard A>=2 rejected this legal boundary before
examining the waveform. It now allows A>=1; idle-clock, direction, full-waveform,
setup/hold and termination checks remain. A hand-authored trace validates the
boundary independently of the instruction model; initial wrong clock and a
clock transition on CS assertion still fail.

Mode3 needs initial high SCK on the same board. Skipping its idle SET fails
the observed idle-before-CS check. This does not change historical E0027's
explicit-idle template counts or E0028's mode0/2 proof.

## Scope and falsification

The frozen family contains one LOOP and four body operations: DRIVE, WAIT,
SET-clock and SAMPLE. All24 body permutations and0..49 wait/sample counts
are timing-filtered, then four GPIO mask choices and the declared prefixes
are assessed. Search rejection uses TX0x96/RX0x69, MSB-first. This is enough
to reject universal acceptance of each tested failing schedule; it is not an
exhaustive ISA search or a minimum-word proof. Shifted iteration attribution,
prepared first bits, head/tail unrolling and other opcodes remain outside scope.

The positive reference sweep pairs RX with TX=(73*RX+19) modulo256. This
covers each byte value and both orders with early/late/mixed responses, not
all65,536 TX/RX pairs. Neither the nine-word nor ten-word reference executes
successfully in the real eight-word hardware.

Every deletion that reduces those references to eight words is publicly
loaded, read back and checked in both simulators. Receiving the right byte
alone is insufficient: mode1 dropping release returns0x69 with valid high but
fails pins/termination; dropping HALT returns0x69 but reaches FAULT. All108
shortened traces exactly match the independent instruction reference and fail
the external oracle. Four additional capacity controls confirm that committing
nine/ten words invalidates ready/length and leaves execution idle.

## Retained evidence and next action

[run-result.json](run-result.json) retains source hashes, commands, elapsed
budgets, accepted references and all case summaries. Canonical full public
traces and reference witnesses are losslessly gzip-compressed; both simulator
logs/JUnit and generated compact input files are retained. The recorded engine
hash remains b429d48e87993f3878aca37f804b2758fa439dc80afc275317e6a10c91d0eaa0.
`checksums.json` hashes every retained file except itself.

Next measure a general GPIO update with selectable delay before/after the
update, as an isolated alternative to storage expansion. Combining two WAIT
words with GPIO updates could make the common explicit-idle phase1 template
eight words. That is a hypothesis requiring encoding/legacy audit, public
simulation, formal controls and area/state measurement, not a new instruction
or achieved hardware result. See [D30](../../docs/decisions/0030-phase1-capacity-and-timed-gpio.md)
and the [frozen experiment](../../docs/specs/spi-phase1-capacity-screen.md).

## Clean remote qualification

Implementation `c54a79551917007d9ab4fbc8546b75424d8a45e0` passes the complete
[SPI gate](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43126561645).
All recorded source hashes match the exact Git blobs. The downloaded artifact
ZIP matches GitHub's SHA-256; the search counts and accepted programs, all
reference witnesses, and all108 public traces plus112 case records match local.
Both simulators have byte-identical records. The prior sensitivity, four-mode
and held-program proof gates also pass with source hashes verified.
See [remote-qualification.json](remote-qualification.json) and
[remote-run-result.json](remote-run-result.json).

## Published research snapshot

[v0.1.0-alpha.3](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.3)
publishes this study at c54a795. Publication run43126569316 passes the locked
workbench ladder and all four focused SPI gates. All seven checksummed assets
match, including the new capacity report. Anonymous registry access succeeds;
the version resolves to the publication manifest's digest, and the OCI revision
label matches the tested source. No full local image pull was needed.
See [release-verification.json](release-verification.json).

The release tag also passes the separate
[full regression](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43126569565),
including the existing hardware comparison, compact formal/refinement,
public integration, pin/input transport and loaded-program invariant gates.
See [full-regression.json](full-regression.json). This repeats existing digital
qualification and adds no physical or full-four-mode claim.
