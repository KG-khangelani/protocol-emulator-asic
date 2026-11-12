# E0031 - Matched 8x4 physical comparison

Status: **matched routed measurements and real-netlist tests recorded; fanout correction and full acceptance pending**.

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
Further local tuning is deferred; fresh official GDS/precheck/netlist evidence
will determine acceptance.

The physical evidence guard now requires finite nonnegative setup/hold at
all three frozen corners and zero final electrical, routing, antenna, power-grid,
Magic and LVS error counts. Regression controls reject the original
green-but-fanout-failing result, missing corners, non-finite measurements and
individual physical failures. Missing results cannot become passes.

The P adoption decision remains **PENDING**. This experiment does not qualify
I2C, continuous UART delivery, owner fluency or fabricated silicon.
