# G1 - Matched 8x4 CMOS5L experiment

Frozen: 2026-11-12, D33; shared electrical correction D34.
Question: does E0030's timed post-action GPIO P retain a complete-chip advantage over compact10 in the current official flow,
and does a candidate meet the 20 ns target after routing?

## Candidates and boundaries

Use the unchanged E0030 builder and compare every generated RTL SHA-256 with
its retained E0030 manifest before running. P has eight program words;
compact10 has ten and a banked loader. Include the complete top, real loader,
stores, input synchronizer and engine. Do not tie off public inputs or preload
constant programs for synthesis. Production RTL remains unchanged.

One manual `gds` workflow run per variant avoids collisions between the official
action's artifact names. Record the workflow revision and staged source hashes:
the staged experimental chip is not the production chip at the Git revision.

## Frozen physical conditions

The candidate lock is `official_cmos5l_8x4` in
`tools/workbench/toolchain.lock.json`. Its historical
`official_cmos5l_qualification` entry stays pinned to E0010.

- Tiny Tapeout action: `5e7361fdc445649261c0725dc15f38242dfad330` (ttihp27a).
- Support tools: `9d13ff3e3e6202090740110438c6a10c1d62ca0f`.
- LibreLane: `3.1.0.dev4`, immutable Linux/amd64 image digest in the lock.
- IHP CMOS5L PDK: `89d42ee6d2fd9b50b86a1aada6fee6673c3e6008`.
  LibreLane's default PDK hash and the official precheck hash agree.
- Metadata: 8x4; template die rectangle `0 0 1724.16 710.64` micrometres.
  This is the template boundary, not usable standard-cell area.
- Clock: 50 MHz / 20 ns. Placement density: 60%; hold margins: 0.1/0.05 ns.
  These placement/timing settings match the audited template. D34 adds shared
  MAX_FANOUT_CONSTRAINT=8, CTS_SINK_CLUSTERING_SIZE=8 and
  CTS_DISTANCE_BETWEEN_BUFFERS=100 micrometres after retained default-flow
  fanout failures. The revised source digest and settings are locked together.
- Same official pin DEF, support-generated constraints, library defaults, corner
  set and tool image for both variants. Retain resolved configuration, libraries,
  corner reports and seeds; abort comparison if these differ unexpectedly.
- Standard synthesis/placement/routing flow, without variant-specific tuning.
  Preserve failed attempts. Limits per run: GDS 180 minutes, precheck 45,
  gate-level simulation 45. An infrastructure retry is recorded separately.

The current template, action, support files, floorplan and PDK-default source
identities are recorded in E0031's upstream audit. Direct actions are pinned;
internally tagged official-action dependencies remain an observed trust boundary.

## Functional qualification

E0030's full RTL and formal evidence remains applicable only when the generated
RTL hashes match exactly. No physical claim follows from that evidence alone.

Use the existing independent expectations against a real mapped netlist:
public-pin reload; bounded input wait and loop kernels; both-order shifting;
UART TX and the six bounded RX/host-service groups; and
`test_spi_timed_gpio.timed_public_programs`. The latter retains all 1,052
transactions: 1,036 phase1 positives, 12 held mode0/2 positives and four expected
edge-only rejections. An expected rejection is a successful negative control,
not positive protocol coverage. Keep the full records and retained corner traces.

Select only public-pin test functions: direct-engine instruction tests cannot
observe the optimized netlist. The same selection must first pass on generated
RTL with `GL_TEST` enabled, so no directly driven engine exists in the harness.
Run the physical tests without filtering their byte sweep. Count the expected
12 required test groups and reject any skipped, missing or failed required
group. Cocotb also lists ten known excluded groups as skipped; retain their
identities separately. Reject unknown groups, duplicate identities or an
excluded group that unexpectedly runs. These excluded groups are not coverage.

These are functional, zero-delay netlist simulations. Routed static timing
reports supply the timing evidence; neither establishes analog pad behavior
or unrestricted SPI input compatibility.

## Measurements and decision

For each variant retain source/configuration hashes, mapped cell area and counts,
final cell area/utilization, storage capacity, setup and hold slack for every
reported corner, violations, precheck and netlist test results, plus artifact
checksums. Keep mapping, placement and final routing stages distinct.
D34 explicitly gates zero final fanout/capacitance/slew, routing, antenna,
power-grid, Magic and LVS violations, plus finite nonnegative setup/hold at
every frozen corner. A green upstream job with a failing count is insufficient.

Route both variants to permit a matched routed comparison. First reject any
candidate that fails a required functional/physical gate. If both pass, compare
complete-chip area, timing and actual capacity without hiding a tradeoff.
Adopt P for the next integration candidate only if its saved storage translates
to a useful measured advantage without losing required behavior or timing.
Otherwise retain compact10 or revise the hypothesis with the evidence.

A passing G1 candidate is an experimental physical qualification, not promotion
of production RTL or completion of shared-core UART/SPI/I2C coverage. Record
the decision in the ledger and state. Preserve all historical 6x4 measurements.
