# D4 — Qualify an immutable physical-flow snapshot

Date: 2026-09-25. Status: adopted for the M0 acceptance candidate.

Need: a branch name such as `ihp-cmos5l` can point to different code tomorrow.
That makes a passing run difficult to reproduce and lets an upstream change
enter the acceptance lane without review.

Decision: pin every action referenced directly by this repository to a full
40-character Git commit. For the physical lane, also pass the E0006-qualified
Tiny Tapeout support-tools commit and LibreLane version explicitly. The pinned
Tiny Tapeout installer in turn fixes the IHP Open PDK commit. Keep those
identities together in `tools/workbench/toolchain.lock.json`, and make the
repository consistency check reject a mutable direct action reference.

Consequences:

- A physical run changes ingredients only through an inspectable repository
  change, rather than silently following an upstream branch or tag.
- The next run is the first repository-pinned qualification run; E0006 remains
  the evidence that selected the candidate revisions, not that clean rerun.
- The pinned upstream composite action remains a reviewed trust boundary. It
  invokes some transitive actions by version tag internally; their resolutions
  observed in E0006 are recorded in the lock, but this repository cannot change
  those references without vendoring or forking the official action.
- A later non-gating canary should follow the upstream branch and report drift
  without changing the acceptance environment.

Rejected: continuing to run acceptance from mutable branch names, or replacing
the official Tiny Tapeout physical flow with generic local synthesis.
