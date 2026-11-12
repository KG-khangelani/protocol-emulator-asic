# E0031 - Matched 8x4 physical comparison

Status: **D34 routed reports verified; P fails fanout, compact10 passes GDS/netlist gates and awaits precheck**.

Question: does the complete timed P chip retain its advantage over compact10
after CMOS5L mapping/routing, and does either satisfy the 20 ns target?

[D33](../../docs/decisions/0033-matched-8x4-physical-experiment.md) and the
[frozen comparison](../../docs/specs/g1-cmos5l-physical-comparison.md) define the
conditions and decision rule. [upstream-audit.json](upstream-audit.json) records
the exact template, action, support, PDK and container identities. The existing
original source configuration matches that template; metadata targets 8x4.
[D34](../../docs/decisions/0034-enforce-cmos5l-fanout-limits.md) records the
subsequent shared fanout correction and its pending qualification.
Historical M0/6x4 evidence and production RTL are unchanged.

## Local preparation

[Local validation](local/validation.json) records the checked scope and retained
failures; [checksums](local/SHA256SUMS) cover its logs, XML, inputs and traces.

Both generated RTL variants match every E0030 source hash. Each passes the
12 required public test groups with the directly driven engine removed from
the testbench. Each retains 1,052 SPI transfers with exactly the E0030 records:
1,048 positives and four expected edge-only negative controls. These are RTL
preflights, not mapped-netlist or physical results.

The evidence checker rejects missing transfers, altered trace hashes, missing
or skipped required groups, unexpected groups and unexpectedly executed excluded
groups. Local staging cannot overwrite production sources; in-place staging
requires a clean GitHub Actions checkout.

The initial test filter was unquoted in a shell command and failed before any
simulation. The corrected harness completed all required tests, but the first
result checker counted ten intentionally excluded discovery records as required.
The checker now records those exclusions separately while enforcing all twelve
required groups. Original logs and the reporting failure remain retained.
No RTL, stimulus or oracle was changed to resolve either harness issue.

The atlas's target allocation was regenerated from metadata. Its old 6x4
fixture was updated, and the initial missing local TypeScript dependency is
recorded separately from chip results.

## Fresh functional and publication checks

The [clean timed comparison](ci/verification.json) at 3868ad2 passes all seven
gates and selects P for the existing scoped experiment. Its archive digest,
671 retained file checksums, generated RTL identities and source-input hashes
were verified. All six P/F/compact10 public record sets match E0030 across
Icarus and Verilator. [Gate records](ci/result.json) and their
[checksums](ci/SHA256SUMS) are retained here; earlier E0030 failures remain.

The [full source regression](ci/main/verification.json) also passes at 3868ad2:
both 22-test RTL runs, existing model/formal checks and all five scoped SPI
gates. Its clean-checkout manifest matches 255 source hashes and 31 retained
artifact hashes. The Windows learning-tools job passes separately; this is
tool validation and does not mark the owner's fluency complete.

The [updated workbench package](workbench-verification.json) also passes its
publication ladder. The downloaded archive, manifest checksums, registry image
digest, Linux amd64 platform and source revision were verified, including
anonymous registry access. This verifies the tools package; alpha.4 remains
the versioned research release. Neither result supplies physical evidence.

The [D34 workbench update](d34-workbench-verification.json) at 29f4b73 also
passes publication. Its archive and asset checksums, image/config digest,
source labels, main and immutable source tags, and anonymous read access to
all thirteen image layers are verified. Layer bodies were not downloaded for
this audit. Both 22-test RTL XML files and the separate one-test harness XML
pass. This publishes the updated tools package; it does not qualify a chip.

The [fresh D34 functional audit](ci/d34/verification.json) verifies the same
29f4b73 source across the full regression, timed comparison and existing SPI
controls. The main manifest matches 257 source hashes and 31 artifact hashes;
both 22-test RTL suites and all eleven collection stages pass. All 671 files
in the timed archive match its checksums, all seven timed gates pass and all
six P/F/compact10 public record sets are byte-identical to E0030. Each record
set contains 1,052 transfers plus a separate candidate-specific control record:
timed instruction controls for P/F, banked non-aliasing for compact10.
The four existing SPI-control gates also pass with checked source identities.
The audit's initial transfer-count assertion counted the control record as a
transfer; the corrected check validates both separately. No simulation input,
oracle or saved result was changed. Inconclusive reachability covers retain
their original status. Physical acceptance remains a separate gate.

## Compatibility scope

The [compatibility audit](compatibility.json) checks the 29f4b73 candidate source
identities against E0030 and the qualified 3868ad2 run. All recorded functional
and formal input files are unchanged except the toolchain lock; its developer
workbench definition is identical. The physical-flow configuration changes
do not alter the generated RTL or those proof obligations.

Both candidates retain nineteen passes and one declared failure in the
original twenty-group legacy suite. P allocates formerly-invalid timed SET
and DRIVE words; compact10 accepts program lengths nine and ten. These changes
are explicit, not a claim of complete backward compatibility.

P has instruction-safety, scoped legal-old-encoding refinement and actual
eight-word public-loaded mode1/3 program induction evidence. That induction
does not prove compact10's ten-word banked loader. Compact10's public
loading/protocol results remain simulation evidence. Both original default-flow
netlists passed the twelve-group public selection. Revised compact10 also
passes all twelve; P's revised workflow skips these tests after its physical
gate fails. The excluded
direct-engine and incompatible legacy groups are not counted as coverage.

Across candidates, the SPI comparison checks pins, direction, received
byte/valid and terminal timing. Intermediate RUN/WAIT states can differ.
The held-response input premise and four expected edge-only rejections stay
explicit. Shared-core I2C and production promotion remain later gates.

## Original template-default physical results

The [retained first comparison](attempts/template-default/comparison.json) uses
implementation 3868ad2:
[P](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43158656790)
and [compact10](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43158660511).
Both official GDS builds and all twelve real-netlist public test groups pass.
Each netlist reproduces all 1,052 E0030 SPI records, including four expected
negative controls. The actual tested/submitted netlist hashes agree.
Both also pass all ten official prechecks; the downloaded report hashes and
individual cases are retained in each candidate's result.

| Complete-chip measurement | P | compact10 |
|---|---:|---:|
| Program words / bits | 8 / 256 | 10 / 320 |
| Mapped cell area, square micrometres | 55,668.8538 | 64,569.0528 |
| Mapped sequential cell area, square micrometres | 20,183.3856 | 23,367.6576 |
| Routed standard-cell area, square micrometres | 65,737.5 | 75,994.3 |
| Routed standard cells | 4,584 | 5,042 |
| Standard-cell utilization | 5.44107% | 6.29002% |
| Worst setup slack at 20 ns, ns | +6.450445 | +3.358149 |
| Worst hold slack, ns | +0.127375 | +0.136927 |
| Final routing / Magic DRC / LVS errors | 0 / 0 / 0 | 0 / 0 / 0 |
| Fanout violations | **30** | **37** |

P saves **10,256.8 square micrometres (13.4968%) of routed standard-cell area**
under these matched conditions. Both resolved configurations are identical,
as are the final timing constraints. This does not shrink the fixed 8x4 die,
and P has two fewer program words. Total instance area includes fill cells;
the comparison uses the explicit standard-cell area metric.

Retained corner reports cover fast/1.32 V/-40 C, slow/1.08 V/125 C and
typical/1.20 V/25 C. The official fallback constraints apply 4 ns input/output
delays, 6 fF output loads and 0.25 ns clock uncertainty. This is evidence for
the declared 20 ns model, not a maximum-frequency or board-electrical claim.
The pinned physical Yosys differs from the developer workbench's generic
synthesis tool; their cell counts are separate measurements.

The green official build does **not** resolve the fanout failures. P's thirty
violations are clock-tree outputs; compact10 has thirty-six clock outputs and
one program-store data buffer. Reports impose a limit of eight loads, with
observed counts up to sixteen. The flow's general fanout default is ten and
clock sink clustering has no explicit count limit.

A bounded local diagnostic tests the same stricter fanout and clock-tree
settings for both chips in the exact pinned image and PDK. All source identities
remain those of E0030. The first clustering change leaves one overloaded clock
root per chip; its final routed counts are one for P and three for compact10.
An explicit 100-micrometre buffer spacing clears the fresh nominal-corner
clock-tree checks and compact10's all-corner routed checks. P retains one
data-buffer violation: detailed-route antenna repair adds four diode loads to
seven functional loads on that net. Database inspection confirms the additions
occur after the earlier clean timing check. A bounded jumper-only antenna
repair trial removes that fanout count but leaves two antenna violations; it is
rejected. [All diagnostic results](attempts/fanout-diagnostics/result.json)
are retained. Normal antenna repair and the three shared D34 settings proceed
to official requalification, with compact10 the locally passing fallback.
Further local tuning is deferred. The [D34 runs](d34-runs.json) are
[P/run43173112351](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43173112351)
and [compact10/run43173116485](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43173116485)
at source 29f4b73. Both completed GDS generation; the additional physical gate
rejects P. Compact10 passes that gate and its public netlist tests; its
independent precheck remains active.

The physical evidence guard now requires finite nonnegative setup/hold at
all three frozen corners and zero final electrical, routing, antenna, power-grid,
Magic and LVS error counts. Regression controls reject the original
green-but-fanout-failing result, missing corners, non-finite measurements and
individual physical failures. Missing results cannot become passes.

## D34 official results

The [revised comparison](attempts/d34/comparison.json) verifies identical
resolved configurations, final timing constraints and actual GDS tool/action
identities. Both generated designs retain every E0030 source identity.

| Complete-chip measurement | P | compact10 |
|---|---:|---:|
| Program words / bits | 8 / 256 | 10 / 320 |
| Mapped cells | 3,926 | 4,289 |
| Mapped cell area, square micrometres | 56,107.9386 | 64,861.1712 |
| Mapped sequential cells | 412 | 477 |
| Mapped sequential cell area, square micrometres | 20,183.3856 | 23,367.6576 |
| Routed standard-cell area, square micrometres | 66,209.3 | 76,230.2 |
| Routed standard cells | 4,493 | 4,938 |
| Standard-cell utilization | 5.48012% | 6.30955% |
| Worst setup slack at 20 ns, ns | +7.444868 | +4.438054 |
| Worst hold slack, ns | +0.124170 | +0.122590 |
| Final routing / Magic DRC / LVS errors | 0 / 0 / 0 | 0 / 0 / 0 |
| Fanout violations | **1** | 0 |
| Required public netlist groups | NOT RUN | 12 PASS |
| Independent official precheck | NOT RUN | PENDING |

P's measured saving is 10,020.9 square micrometres, or **13.1456% of routed
standard-cell area**, with two fewer program words on the same fixed die.
It fails the acceptance rule. The [submitted-netlist diagnosis](attempts/d34/P/fanout-diagnosis.json)
confirms seven functional loads plus four antenna diodes on `_0601_`, driven
by `_3840_/X`: eleven loads against a limit of eight at every corner. The
upstream build completes, but the added metric guard fails the job and its
dependent precheck/netlist jobs are skipped. These skips are not passes.

Compact10 clears every required routed metric and reproduces all 1,052 E0030
SPI records in its real-netlist test, including the four expected negative
controls. Its tested and submitted netlist hashes match. The official log
also confirms the exact downloaded submission archive, source checkout,
PDK cache identity and compiled physical-cell models. Official GL uses the
observed Icarus 13.0/cocotb 2.0.1 environment, separately from the developer
workbench. Tagged transitive actions remain an observed trust boundary.
Retained job logs redact URL query strings; original and retained log hashes
are recorded separately. [Audit notes](attempts/d34/audit-notes.json) explain
the corrected provenance-check assumption and observed action identities.

P is ineligible for adoption under this frozen flow. The final decision and
compact10's full qualification await its precheck. This experiment does not qualify
I2C, continuous UART delivery, owner fluency or fabricated silicon.
