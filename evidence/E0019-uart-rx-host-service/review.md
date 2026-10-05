# Independent bounded-host review

2026-10-05; read-only independent agent `uart_independent_review`.

Policy review: CLEAN. Worst detection delay H-1 makes H+L<=10P sufficient
for first copy by C2-1. The first cache precedes HALT; completion bound
HALT+H-1+L is valid. Quarantine, raw-valid versus acceptance, pin ownership
and external-storage/physical limits are explicit.

Implementation review found one verification blocker: a diagnostic snapshot
outside the main driver's final cycle stretched the first post-HALT rising
interval to 20,005ps. This did not invalidate clock-count arithmetic, but
contradicted the exact-time test claim. The finding is retained here.

Correction: skip the outside-cycle diagnostic when continuing host service,
match the main driver's +1ps rising alignment in terminal cycles, and assert
exactly 20,000ps between EVERY observer edge (including non-read/HALT handoff).
Fresh focused Icarus on this source passes all three host groups; report is
`focused-results-icarus.xml`. There was no production RTL defect/change.

Independent re-review: CLEAN, no remaining correctness blocker. Coincident
poll/copy does not reschedule/lose reads; tentative data is discarded on
fault/abort; postacceptance disable does not revoke delivered bytes; observer
receives only scheduled public reads; late traces expose overwrite loss.
Independent unit rerun passes three groups, including 780 P4 boundary residues.
Reviewed `test/test_uart_rx_public.py` SHA-256:
`024d609a265d9b8f23a011fcb0d96bec9baca4afff2f9e3067d0ee738c8f1e9e`.

Coherent frozen-source local/clean CI remains a distinct release gate, not
inferred from review or focused tests. This is not physical/owner-fluency evidence.

Evidence audit at implementation `9379d686fb37f912a4beb874c0f506b2f5d2541f`:
all 31 ORIGINAL local artifacts verify; curated manifest has the same hash.
132/136 original local source hashes match the implementation commit; four
post-run documentation differences are explicitly covered by exact-head CI.
The P434 table is correct and production RTL is unchanged. Refine stale
local-pending prose, expected mutant FAIL interpretation and JUnit terminal-LF
normalization in the final record; no implementation blocker was found.
The record now includes those refinements and original/curated JUnit hashes.

Final record re-review: CLEAN. Independently verified the clean implementation
head, all 31 original CI artifact hashes, all 136 committed-source hashes,
explicitly normalized JUnit copies, required formal outcomes and unchanged
generic cost. Only docs/evidence changed; ZIP attribution, final-record CI/
integration still pending, physical limits and M0 fluency are distinguished.
