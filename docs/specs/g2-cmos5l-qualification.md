# G2 - Complete shared-core physical qualification

Frozen 2026-11-12 before the first G2 physical run. D37/E0035 advances od128;
E0036 audits the clean 31ebf82 regression. A physical run is an experiment,
not production promotion or a substitute for the remaining formal gate.

## Candidates and fixed conditions

Generate the exact five RTL files recorded in E0035's current source manifest.
Include the real public loader, all allocated program words, data store,
synchronizer and engine. od128 has 128 words / 4,096 program bits;
literal255 has 255 words / 8,160 bits. No constant program preload or tied
public input is permitted. Copy into `src/` only in a clean CI checkout.
The workflow revision and staged file hashes together identify each chip.

Run the two variants separately through `gds-g2`, avoiding collisions in the
official action's artifact names. Preserve `gds` as the historical G1 workflow.
Use the unchanged `official_cmos5l_8x4` lock and `src/config.json`: 8x4,
20 ns clock, the same die, pin constraints, 60% placement density, three
corners, 0.1/0.05 ns hold margins and D34's shared fanout/CTS settings.
The pinned action, support revision, LibreLane image and PDK remain identical
to G1. Verify the resolved configuration and physical identities after each
run. Internal tagged action dependencies remain an observed trust boundary.

Retain mapping, placement and routed area/counts separately, actual storage,
all-corner setup/hold, utilization, violation counts, original artifacts and
their hashes. Compare complete-chip mapped cost for both candidates. Claim a
routed saving only if both have routed measurements under matching conditions.
A literal255 capacity/physical failure remains a measured rejected result;
od128 must pass every production gate. No threshold, corner, footprint, clock
or antenna rule is relaxed to obtain a pass.

## Required od128 public netlist regression

Run the existing independent expectations against the actual submitted CMOS5L
netlist, first verifying this exact selection on generated RTL without the
directly driven engine. Require eighteen groups:

- The twelve G1 public kernel, UART TX, bounded UART RX/host-service and
  four-mode/both-order SPI groups, including all 1,052 SPI transfers.
- The full I2C sweep: 1,160 records, with 996 OK, six NACK, 152 bounded timeout
  outcomes and six expected rejected controls. Preserve every byte, ordinary
  address, stretching position and before/final/late/permanent deadline case.
- Four public architecture groups covering real storage banks/bytes/lengths,
  full PC, failure branches/overflow, interrupted partial state and the
  160-case open-drain/alternate-payload sweep.
- Eighteen reset/disable/isolated-loader aborts and eighteen fresh public
  reload/recovery transactions, all in the existing abort group.

Require exact equality with the audited E0036 RTL records, including trace
hashes and expected failures. Reject missing, duplicate, failed or skipped
required groups. The ten explicitly excluded direct-engine/instruction groups
remain listed separately; reject unknown exclusions or unexpected execution.
Preserve UART service/framing/delivery limits and SPI input-hold assumptions;
the four edge-only SPI failures are negative controls, not protocol coverage.

These are functional zero-delay netlist simulations; routed static timing
provides the separate delay evidence. Neither establishes analog pad behavior,
RC loading, spike filtering, metastability bounds or unrestricted input timing.

## Acceptance and limits

Require every frozen final routing/electrical/antenna/power-grid/Magic/LVS
violation count to be zero, finite nonnegative setup/hold at every corner,
all ten official prechecks and the full netlist selection above. Match tested
netlist bytes to the submitted archive. Retain seeds, source/configuration
identities, failures and witnesses. A green upstream job alone is insufficient.

Bound each GDS run to 180 minutes, precheck to 45 and the full od128 netlist
run to 180. The larger simulation allowance reflects the increased real
storage and test matrix; it changes no hardware timing or test coverage.
literal255's physical run is a cost comparison; its netlist protocol
qualification is not required to adopt od128 and must not be inferred.

Production promotion still requires the same candidate's combined RTL
regression, relevant unbounded formal proofs, all physical gates above, a
documented integration decision and verified milestone publication. Preserve
G1's compact10 qualification/P rejection, historical 6x4 evidence and the
separate pending owner-fluency outcome.
