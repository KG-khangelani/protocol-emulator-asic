# G4 final submission candidate

<!-- G4 physical qualification from retained E0047 records -->
**G4 COMPLETE 2026-11-14: fresh physical reproduction, software distribution,
verified stable publication and submission packet. No entry has been sent.**

Both predeclared production runs at `45c55f7cd95db2a883b0ffb5e864decd62d53601` pass
the complete physical, official-precheck and actual-netlist public gates.
All twenty frozen physical inputs remain unchanged. Each run retains its six
original archives, exact producer/runtime identity, frozen audit dependencies,
Windows/Linux replay and nine rejected evidence-corruption controls.

The [original isolated Linux CI proof](linux-ci-43554467650/README.md) retains
the genuine commands, output and public-image identity for both Linux replays.
The [host interruption](host-runtime/README.md) preserves the local startup
failure and reversible relocation of inactive generated files.

[Corrected package CI](package-ci-43557808053/README.md) and the native Windows
run produce 17 byte-identical assets at release source `5bdc0e6`; the bundle has
435 members. Its standalone assembler rebuilds thirteen examples into 52
identical files. The [initial checksum-order mismatch](package-portability/README.md)
remains rejected. Annotated `v0.1.0` now identifies the corrected source;
all nine release-tag workflows and public-download/image verification pass.

| Role | Original files / frozen inputs | Prechecks / public netlist groups | Fault controls |
|---|---:|---:|---:|
| [Candidate 43543626249](ci-43543626249/README.md) | 1,729 / 84 | 10 / 18 | 9 rejected |
| [Reproduction 43543629839](ci-43543629839/README.md) | 1,729 / 84 | 10 / 18 | 9 rejected |

Both report +5.595886 ns setup slack and +0.120791 ns hold slack at the 20 ns
target, with 61,294.1 square micrometres of routed standard-cell area.
Required physical and electrical violation counts are zero.
The flow has 85 configured entries, 77 executed top-level stages, 2 nested antenna stages and 8 frozen gate-disabled entries.
The frozen conditional skips remain separate from executed gates.

The [complete reproduction record](reproduction.json) binds both results.
Only 764 bytes across 191 BGNLIB/BGNSTR timestamp records differ; all 995,697 GDS records have the same structure and all geometry records agree.
Submitted netlists, timing/area and all recorded stage configuration/state
bytes agree. 1,052 SPI, 1,160 I2C, 4 boundary and 36 abort records agree.
UART groups run their assertions; the retained comparison consists of
97 RX/late-reader landmarks, not complete UART TX waveforms.

G2 continuity remains a separate historical comparison. Its original geometry
agrees after timestamp normalization, and its netlist, physical inputs,
timing/area and public record hashes agree. Original G1-G3 records and rejected
experiments are preserved.

[Fresh program-tool CI](program-tools/README.md) passes at `ae2ac7bf800bd02d83fe62677a56bc4131e98b06`,
run 43544749692: 20 assembler tests, 55 cases per simulator including
15 expected rejections, and 53 identical Windows/Linux compiled files. All
352 producing inputs are frozen for final-release comparison.

The [submission packet](../../docs/submission.md), current guides and prepared
`v0.1.0` distribution describe these results and their limits. The physical
producer revision above is distinct from the later immutable release source;
the package manifest and unchanged-input checks bind that relationship.

<!-- G4 publication closure from retained evidence -->
Publication is verified for stable `v0.1.0` at release source `5bdc0e6b6449a829a5da1f8f9a8060257e974843`. All 35 public assets, 435 bundle members and the matching workbench image/source identities pass; all nine tag workflows / 22 jobs pass. Windows and Linux produce 17 byte-identical assets, and the standalone bundle rebuilds all thirteen examples into 52 identical files. See the [publication audit](publication/README.md) and [completion audit](completion-audit.json).

The [rejected initial package comparison](package-portability/README.md)
exposed Windows/Linux filename-order differences in the checksum list.
Explicit filename sorting corrected it before the release source was tagged.
The [current rules observation](rules-closure-observation.json) matches the
activation page; the final submission form remains forthcoming.

The executed completion checker is retained as `completion-runner.py.gz`.
Restore it to `build/complete_g4.py` in a complete checkout and run
`python build/complete_g4.py --check-only` to check all five requirements
without replacing the original audit. `release-upload.json` and its compressed
runner/log retain the actual seventeen-asset upload; the independent publication
audit verifies the resulting public files.

These are digital physical-flow, static-timing and zero-delay netlist results.
The mixed fast-temperature boundary, UART host service, SPI input hold and
I2C external pull-up assumptions remain. No silicon, analog compliance,
measured Fmax, owner fluency or actual competition entry is claimed.

## Activation and earlier checkpoints (historical)

The following text preserves the state recorded before complete qualification;
the current result is the qualified checkpoint above.

Current checkpoint: both official runs pass GDS, all ten prechecks and all
eighteen actual-netlist public groups. Each original six-ZIP set contains 1,729
members and freezes 84 producing inputs. Their complete audits and Windows
replays pass; the candidate's nine corruption controls pass. The [complete
comparison](reproduction.json) reproduces netlists, geometry apart from standard
timestamps, timing/area, stage configuration/state and retained public records.
G2 continuity is separately preserved. Linux replay and publication remain
pending. Local Docker container creation failed after a host disk-capacity event;
isolated Linux CI will use the previously verified, immutable public workbench
image. The cause of the host failure is unconfirmed.

The following paragraphs preserve earlier checkpoints and their then-open gates.

Activated 2026-11-14 from G3 closure `59dd1dc` under
[D49](../../docs/decisions/0049-freeze-g4-submission-candidate.md) and the
[predeclared contract](../../docs/specs/g4-submission-candidate.md).

The freeze record preserves all twenty qualified physical inputs, metadata,
workflow and pinned toolchain identities. The current official rule observation
is separate. No fresh G4 physical result is claimed at activation.

Two clean official production runs are building source `45c55f7`:
[candidate43543626249](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543626249)
and [reproduction43543629839](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543629839).
Their identities were registered before results. Original GDS/precheck/public-netlist
results, source/runtime identity, independent replay and comparisons remain pending.
A stable release follows only after every required gate passes.

The current [submission account](../../docs/submission.md), architecture/ISA,
verification and AI-use guides are prepared. The independent stage audit records
85 configured entries, 77 executed top-level stages, eight frozen gate-disabled
entries and two nested antenna stages in the qualified G2 baseline. These counts
remain distinct; no checker is disabled for G4. The GDS comparison controls accept
only a timestamp edit and reject a coordinate edit and invalid timestamp datatype.
The release packager and verifier are prepared, with full execution awaiting the
actual fresh results and final release.

[Fresh program-tool CI](program-tools/README.md) passes at `ae2ac7b`, run43544749692.
The two original archives retain 226 members; all 352 producing inputs are
frozen, including the unchanged 351 G3 inputs. Both simulators' 55 cases and
the 53 Windows/Linux compiled files match G3. Windows and pinned-Linux replay
agree, and five deliberate corruptions are rejected on each platform.

The [first completed layout checkpoint](layout-continuity-checkpoint.json)
audits reproduction run43543629839's original GDS archives. Its complete
physical conditions pass; netlist and timing/area equal G2. The layout differs
from G2 only in 191 standard timestamp records (1,146 bytes); all other GDS
records are identical. This checkpoint is explicitly incomplete qualification:
precheck, public netlist tests and the independent candidate remain required.

The [two-build layout checkpoint](layout-pair-checkpoint.json) compares the
original submitted layouts from both fresh runs. All 995,697 GDS records have
the same structure; only 764 bytes across 191 timestamp records differ. The
netlists, timing/area and every recorded stage configuration/state are identical.
Both official precheck jobs have also completed successfully. The complete
public-netlist tests and retained full audits are still pending, so this is
not a completed G4 qualification.

G1-G3 evidence, rejected trials, alpha.6 hardware adoption and alpha.7 software
qualification remain unchanged. G4 ends at submission readiness: no entry is
sent and no owner fluency or fabricated-silicon result is inferred.
