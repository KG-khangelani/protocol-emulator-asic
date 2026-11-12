# D35 - Choose a physically qualified integration baseline

Date: 2026-11-12. Status: adopted for the experimental physical pilot; production promotion remains gated by G2.

## Decision

P is not adopted under the frozen D34 flow. Its smaller routed standard-cell
area does not compensate for a failed electrical limit. Select compact10 for the next shared-core integration step. It passes the
official GDS, routed-metrics, precheck and real-netlist public-pin gates.
Production RTL is not promoted by this decision.

## Matched complete-chip evidence

Both official attempts use workflow source
29f4b73ae66d2b955f512b5be250f6ed0afcdab8 and E0030-identical generated RTL.
They include the real program/data stores, loaders, synchronizers and engines.
The resolved configurations, final timing constraints and actual GDS tool/action
identities match. The common D34 controls, 8x4 die, libraries/corners, pin DEF,
20 ns clock target and normal antenna protection are unchanged between variants.

| Measurement or gate | P | compact10 |
|---|---:|---:|
| Program capacity, words / bits | 8 / 256 | 10 / 320 |
| Mapped cells | 3,926 | 4,289 |
| Mapped cell area, square micrometres | 56,107.9386 | 64,861.1712 |
| Total mapped sequential cells | 412 | 477 |
| Total mapped sequential area, square micrometres | 20,183.3856 | 23,367.6576 |
| Routed standard-cell area, square micrometres | 66,209.3 | 76,230.2 |
| Routed standard cells | 4,493 | 4,938 |
| Standard-cell utilization | 5.48012% | 6.30955% |
| Worst setup / hold slack, ns | +7.444868 / +0.124170 | +4.438054 / +0.122590 |
| Final fanout violations | **1** | 0 |
| Other required routed physical checks | PASS | PASS |
| Official GDS job including acceptance guard | FAIL | PASS |
| Required real-netlist public groups | NOT RUN | 12 PASS |
| Official precheck | NOT RUN | 10 PASS |

The sequential area is the complete chip's register area, not an isolated
program-store estimate. P saves 10,020.9 square micrometres, or 13.1456% of
routed standard-cell area, while offering two fewer program words. This does
not reduce the allocated die. The timing result applies to the declared
50 MHz/20 ns model and corner/input/output constraints, not a measured maximum
frequency or board-electrical guarantee.

P's submitted netlist confirms seven functional loads plus four antenna diodes
on one data-buffer output, giving eleven loads against the limit of eight at
every checked corner. The metric guard fails its job and the dependent jobs
are skipped. The original default-flow 30/37 fanout failures and the local
jumper-only trial's two antenna failures remain retained. No threshold,
clock, capacity or antenna requirement was relaxed to obtain a passing chip.

Compact10's real-netlist run passes all twelve required public groups and
reproduces all 1,052 E0030 SPI records: 1,048 positives and four expected
edge-only negative controls. Its submitted/tested netlist hashes match, and the
consumer log verifies the exact archive, source, PDK selection and actual
physical-cell model compilation. All ten independent official prechecks pass;
the precheck log confirms the same downloaded submission archive and pinned
PDK selection. The qualified layout SHA-256 is
`49ac637e176bbc5c3cf8daefbc4143578015466ef68e1d87c8605ca91da01ab8`.

## Compatibility and next gate

This is an experimental physical pilot, not a completed multi-protocol product.
The old twenty-group legacy suite retains nineteen passes and one declared
failure per candidate: P allocates formerly-invalid timed encodings; compact10
accepts nine- and ten-word program lengths. Neither is advertised as fully
backward compatible.

P's eight-word actual-program induction does not prove compact10's ten-word
banked loader. Compact10's public loading/protocol coverage is simulation
evidence. SPI input-hold assumptions and negative controls remain explicit;
intermediate RUN/WAIT states are not part of the cross-candidate trace equality.

After G1 publication, G2 must freeze the I2C contract/oracle, then demonstrate
the mandatory UART/SPI/I2C workload matrix through programs on one candidate
revision. Promotion requires combined regression and fresh physical evidence
for that revision. The old 6x4/M0 evidence and separate owner-fluency gates
remain intact. Further P tuning is deferred unless a concrete later bottleneck
justifies a new bounded experiment.

## Evidence

- [E0031](../../evidence/E0031-8x4-physical-comparison/README.md)
- [Matched D34 comparison](../../evidence/E0031-8x4-physical-comparison/attempts/d34/comparison.json)
- [P failure and source identities](../../evidence/E0031-8x4-physical-comparison/attempts/d34/P/result.json)
- [Compact10 result and source identities](../../evidence/E0031-8x4-physical-comparison/attempts/d34/compact10/result.json)
- [Compatibility scope](../../evidence/E0031-8x4-physical-comparison/compatibility.json)

Direct flow inputs are pinned; the official composites' internally tagged
dependencies remain an observed trust boundary with their resolved identities
retained. This decision claims no I2C qualification, continuous UART delivery,
fabricated-silicon result or owner fluency.
