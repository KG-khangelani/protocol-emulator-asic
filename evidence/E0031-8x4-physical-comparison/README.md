# E0031 - Matched 8x4 physical comparison

Status: **upstream audit and local public-harness preflight pass; physical results pending**.

Question: does the complete timed P chip retain its advantage over compact10
after CMOS5L mapping/routing, and does either satisfy the 20 ns target?

[D33](../../docs/decisions/0033-matched-8x4-physical-experiment.md) and the
[frozen comparison](../../docs/specs/g1-cmos5l-physical-comparison.md) define the
conditions and decision rule. [upstream-audit.json](upstream-audit.json) records
the exact template, action, support, PDK and container identities. The existing
source configuration matches the current template; metadata now targets 8x4.
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

## Physical work still required

Run one official workflow per variant from the same implementation commit.
Check resolved inputs, actual netlist test results, precheck, mapped area and
post-route timing/violations. Compare both routed designs before claiming a
routed saving. Keep failed runs and immutable artifact checksums.

Until these records exist, mapped area, routed timing and the P adoption
decision remain **NOT_EVALUATED**. This experiment does not qualify I2C,
continuous UART delivery, owner fluency or fabricated silicon.
