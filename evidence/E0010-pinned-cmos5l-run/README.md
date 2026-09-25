# E0010 — Repository-pinned CMOS5L qualification run

GitHub run [36118046477](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36118046477)
tested commit `9ec2200410610cb107372cf7f6ec4d493448049f` on 25 September
2026. It started from a clean GitHub checkout and used the physical-flow inputs
locked in this repository. GDS generation, gate-level regression, and every
Tiny Tapeout precheck passed. The recorded result is **PASS**.

## What passed

| Stage | Plain-language question | Result |
|---|---|---|
| GDS build | Can the RTL become placed and routed CMOS5L geometry? | PASS |
| Gate-level test | Does the generated cell netlist still satisfy the two M0 pin-behaviour tests? | PASS |
| Precheck | Does the layout satisfy the nine Tiny Tapeout submission checks? | PASS |
| Viewer | Was the optional GitHub Pages viewer published? | SKIPPED BY POLICY |

The GDS job ran from 09:22:22 to 09:58:43 UTC. The two gate-level tests ran for
31,220 simulated ns and passed. All nine prechecks passed. The workflow used:

- Tiny Tapeout GDS action commit
  `3412659307918422f3f0727917cf9b499aaca588`;
- support-tools commit `d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`;
- LibreLane `3.1.0.dev3`;
- IHP Open PDK CMOS5L commit
  `2bbec755dc67ca3db0261c3d6163e15735d66710`; and
- physical-flow Yosys 0.66 commit
  `86f2ddebce7e98ce7cacc27e8a5c14cb53b51b51`.

The design maps to 58 synthesis cells (803.7792 µm²) and finishes with 80
placed standard cells (1,166.66 µm²). Standard-cell utilization is 0.129282%.
Worst reported setup slack is +13.585833 ns and worst hold slack is +0.172078
ns at the 20 ns target. Route DRC, Magic DRC, LVS, antenna, setup, and hold
violation counts are zero.

In plain language, synthesis produced a CMOS5L logic bill of materials;
place-and-route fitted and connected it in the allocated tile; timing analysis
reported positive margins for the requested target; precheck accepted the
submission structure; and functional simulation of the generated gates
preserved the two tested M0 behaviours.

## Reproduction, not just another green badge

E0006 and E0010 are two complete official physical-flow passes from clean
GitHub checkouts under the same resolved action, LibreLane, PDK, RTL, and test
inputs. E0006 reached the action through a mutable branch reference; E0010
removes that ambiguity by selecting the action commit directly from the
repository workflow.

Their recorded physical metrics are identical. Their final GDS files have
different whole-file SHA-256 hashes because 192 bytes changed in one `BGNLIB`
and 31 `BGNSTR` timestamp records. Both contain 393,577 GDS records and have
the same timestamp-normalized SHA-256:
`88ff4f42424eaf1656a84c10901d1f0d4ed241b22b5be90c976d85fdf9c3a234`.
No geometry or other non-timestamp record differs.

The rendered layout is visually dominated by the regular fill and power-grid
field required across the fixed 6x4 tile, with the small M0 logic region near
the upper edge. That image is a useful orientation aid; the machine reports,
record comparison, and checks—not visual inspection—support the acceptance
claim.

The seven physical inputs also have identical Git blob IDs at the run commit
and repository commit `40466485f879e0c1efe6183b98764540d84e9afc` checked while
curating this record. Later work in between changed evidence, documentation,
formal checks, and developer infrastructure, not the physical RTL,
configuration, tests, or GDS workflow.

## Claim boundary

This satisfies the **technical** M0 physical-flow gate: a corrected complete
run and its clean repository-pinned reproduction both pass. M0 itself remains
open until the owner completes the fluency teach-back checkpoint.

The result does not establish a maximum clock frequency, analog behaviour,
foundry signoff, fabricated-silicon behaviour, or protocol-emulator capability.
The gate-level run is functional rather than delay-annotated, the 50 MHz value
is a flow target rather than a measured limit, and LibreLane reported use of a
generic fallback SDC. M0 is still a GPIO counter; no UART, SPI, I2C, or temporal
VM is implemented.

Large downloaded artifacts remain under ignored
`build/artifacts/E0010-pinned-cmos5l-36118046477/`. GitHub reports that the
original artifacts expire on 24 December 2026. `result.json` identifies those
artifacts and hashes; this directory retains the small results needed to audit
the claim after that date.
