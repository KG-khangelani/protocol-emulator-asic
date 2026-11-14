# G4 final submission candidate

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

G1-G3 evidence, rejected trials, alpha.6 hardware adoption and alpha.7 software
qualification remain unchanged. G4 ends at submission readiness: no entry is
sent and no owner fluency or fabricated-silicon result is inferred.
