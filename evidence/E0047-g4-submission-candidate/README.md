# G4 final submission candidate

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
