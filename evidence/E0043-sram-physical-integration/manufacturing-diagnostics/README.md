# E0043 - Diagnose manufacturing failures before repeating qualification

The original official physical run fails. Independent examination of the actual
local routed database finds 17 positive-area overlaps between public signal
pins and power stripes. Including Metal4's 0.42 micrometre clearance requirement,
24 violations are detected. The official LVS report has exactly 17 fewer
layout nets than reference nets. Passing power continuity and routing checks
did not establish that public pins were isolated from power.

The declared repair removes `-extend_to_boundary` only from the standard-cell
grid's Metal4 stripe commands. Native PDN generation then ends those stripes
at the core boundary. X positions, widths, macro stripes, all 144 SRAM edge
bridges and all fixed public pins are preserved. The fresh power pilot passes
in 38.405 seconds. Continuing the native sequence through `Odb.ApplyDEFTemplate`
creates all 43 public pin rectangles; their geometry is identical to the
original, and all overlap/clearance checks now pass. The first attempt to
check pins immediately after power generation fails because the pin geometry
does not exist yet. The new full-flow guard is placed after the DEF template.

A separate import diagnostic uses the pinned PDK's `read_sram_gds.tcl`, which
prescribes seven subcell-flattening patterns. On the real
`RM_IHPSG13_1P_BITKIT_16x2_SRAM` subcell, the unchanged full Magic rule deck
reports 232 errors with the original import and zero with the prescribed
import. Adding an undersized Metal2 shape still produces the expected M2.d
error. No rule is disabled. Both earlier 120-second whole-macro trials remain
timeouts without a verdict; subcell success does not qualify the whole macro.
The first macro launch error and the rejected wrong-target diagnostic are
also retained.

Local full trials 03 and 04 use the known-invalid power geometry and are
deliberately stopped, with original partial results and explicit stop records.
A fresh guarded trial 05 combines the validated core endpoints, vendor import
and a mandatory read-only pin/power checker, retaining all 80 original Classic
stages and the three existing project stages. Its complete manufacturing
result is still required. Production remains unchanged.

The archive retains 342 files, including the actual old and corrected
databases, exact runners and decisions, controls, source/configuration copies,
native logs/metrics and completed-container observations. Verify it first:

```text
python evidence/E0043-sram-physical-integration/manufacturing-diagnostics/verify.py --output build/sram-manufacturing-replay
```

Then run the native replay in physical image
`sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5`,
with the repository at `/workspace`:

```text
python3 evidence/E0043-sram-physical-integration/manufacturing-diagnostics/replay_native.py --directory /workspace/build/sram-manufacturing-replay
```

The native replay reproduces all 24 original clearance failures, zero
corrected failures and both fresh passing power-grid checks. This qualifies
the scoped repair trial, not the complete physical design.
