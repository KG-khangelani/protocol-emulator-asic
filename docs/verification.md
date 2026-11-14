# Verification of the production candidate

The production target is the D48-qualified **od128-sram** core, interface
**0x22**. Default commands inspect the actual `src/` files and the hash-checked
SRAM models. [The production guard](../tools/production_sram.py) binds twenty
physical inputs to [G2's qualification](../evidence/E0045-g2-sram-qualification/README.md).
The manual `gds` workflow now builds that production profile. The old P,
compact10 and register-store trials remain separately identified experiments.

G2 establishes the hardware baseline; G3 establishes the assembler and examples.
[G4](../evidence/E0047-g4-submission-candidate/README.md) tracks fresh official
production runs, reproduction and final distribution checks. Its new results
must be read there; the earlier passes below do not imply G4 completion.

## What each layer establishes

| Layer | Check and retained evidence | Boundary |
|---|---|---|
| Source identity | Production guard, profile hashes and stage-specific input maps | Matching bytes alone do not establish behavior |
| Repository checks | Metadata, clocks, supported source profile, model/oracle and assembler acceptance tests | G3's complete check has 147 tests; its 20 assembler tests are included in that count |
| RTL simulation | Icarus and Verilator each run all 30 current groups; [E0042](../evidence/E0042-sram-prefetch-screen/README.md), [E0044](../evidence/E0044-sram-current-verification/ci-13660ac/README.md) and actual-default [E0045 CI](../evidence/E0045-g2-sram-qualification/ci-default-75c1e7d/README.md) | Digital RTL and vendor functional SRAM models, not pad/electrical characterization |
| Programs through public pins | [G3/E0046](../evidence/E0046-program-toolchain/README.md): 13 sources, complete generated load/readback plans, 55 cases per simulator including 15 expected rejections | A tested software interface, not a fabricated-chip host adapter |
| Formal properties | Source-matched engine, support, SRAM/prefetch obligations, checked counterexamples and separately retained historical baseline | Written properties under explicit assumptions; no blanket proof of every protocol or program |
| Generic synthesis | Yosys structural checks, no inferred latches, actual SRAM black box and 353 register bits | Generic cells are not technology area or routed timing |
| Technology mapping | Matched [E0042 mapping](../evidence/E0042-sram-prefetch-screen/README.md) counts standard cells and adds the real macro footprint | Mapping alone does not prove routability |
| Routed physical design | [E0045 official run](../evidence/E0045-g2-sram-qualification/ci-94a3082/README.md): timing, fanout, slew, capacitance, DRC, LVS, power-grid and antenna limits | Exact pinned digital flow and libraries, not measured Fmax or silicon |
| Official precheck | All ten required tests on the actual submitted layout | Complements the complete in-flow checks |
| Public netlist simulation | E0045 passes 18 selected public groups using the actual submitted netlist and SRAM models | Functional zero-delay simulation, not a timing-annotated gate simulation |
| Distribution and replay | Original archive digests, all member hashes, exact source, observed runtime, frozen replay dependencies and corruption controls | A replay rechecks retained evidence; it does not rerun place-and-route |
| Owner learning | Learning-status checks reject an unearned fluency promotion | Tool success does not establish the owner's understanding |

The separate `GL_TEST`-shaped harness smoke test compiles **RTL** with direct
engine access absent and emits its own FST/JUnit. It checks the harness and
public reset behavior. It is never counted as the actual-netlist test above.
The full current RTL suites retain normalized public traces; the smoke waveform
does not substitute for those observations.

## Independent observations and deliberate failures

Protocol oracles check externally visible frames, bus edges, directions,
ownership, timing and results without using the DUT's internal PC to invent
the expected wire trace. UART checks framing and bounded host delivery. SPI
checks every mode/order under its declared input-hold envelope. I2C checks
resolved SCL/SDA, open-drain ownership, ACK/NACK, stretching and cleanup.
Both simulators reproduce 1,052 SPI, 1,160 I2C, four boundary and 36 abort
records from the frozen contracts. These counts include the contracts'
deliberate negative cases; they are not counts of universally successful
transactions.

G3 additionally compares assembled words with independently encoded historical
programs and compares all normalized observations between simulators. Windows,
Linux and a clean clone reproduce the same 53 generated program artifacts.
Changed UART timing, bad framing, edge-only SPI input, changed sample delay,
active-high I2C drive, wrong timeout and interface/readback mismatches must be
rejected. The checker must detect the intended failure, not merely any crash.

The SRAM tests cover every logical byte address, partial writes, reset/reload,
bank/length boundaries, clocked readback, stale fetch tags and word-zero
startup. Actual faulty implementations test retained validity on reset, stale
lanes, current-PC rather than next-PC fetch, and a missing word-zero shadow.
Formal counterexamples include a real partial-write-mask error. Inconclusive
complete-chip equivalence attempts remain inconclusive; the later compositional
proofs and successful regressions do not rewrite those attempts.

"Independent" here describes separately constructed expectations and tool
implementations. It does not mean the project received an independent human
certification; see [AI use](ai-use.md).

## Physical acceptance and reproduction

The frozen flow retains 85 configured stage entries: the original 80 plus five
project integration entries. Conditional stages can be skipped by the pinned
configuration; a configured entry is not an executed check. The audit must
inspect actual stage artifacts and gate results, and distinguish those expected
skips from a missing required gate.

The SRAM integration retains the documented power connections, nine native
input buffers, public-pin clearance checks, exact Magic contact-rule alignment
and selection of existing full-height supply ports. The original complete
Magic checker, LVS and all required electrical limits remain enabled. The
fast model combines -40 C standard cells with -55 C SRAM; this is an explicit
mixed-temperature model boundary, not isothermal characterization.

At G2's qualified source, routed setup slack is 5.5958856909900625 ns and hold
slack is 0.12079138031701087 ns at the 20 ns target. G4 must measure its own
runs. Its [predeclared contract](specs/g4-submission-candidate.md) requires two
clean official builds of the same candidate, all six original archives per
run, source/runtime checks and comparisons of layout, netlist, metrics and
public traces. GDS normalization may remove only BGNLIB/BGNSTR timestamp
fields; geometry changes cannot be labelled identical reproduction.

An official passing badge is insufficient. Retained audits bind producing and
consuming jobs to original archive identities, reconstruct the exact submitted
GDS/netlist and check semantic results. G2's five evidence-corruption controls
reject an unfinished workflow, wrong archive digest, rehashed power-port count,
skipped required test and changed submitted netlist. G4 requires its own
retained replay and controls.

## Run or inspect the checks

With Docker running, use the locked workbench from a clean checkout:

```powershell
.\tools\workbench.ps1 All
.\tools\workbench.ps1 Evidence
.\tools\workbench.ps1 ProgramTest
```

The Linux equivalents are `./tools/workbench.sh All`, `Evidence` and
`ProgramTest`. `All` runs doctor, repository checks, scoped lint, both RTL
simulators, formal checks and synthesis, including the separate harness smoke
test. `Evidence` validates and collects the eight source-bound production
stage receipts, always rerunning the repository check and rerunning other stale
or missing work. `ProgramTest` independently
exercises the assembled examples. [Toolchain and reproduction](toolchain.md)
describes outputs, physical runs and replay commands.

Keep failures, seeds, source hashes, commands, actual tool identities and the
smallest useful witness. Scope changes need a new declared experiment. Neither
an expected-failing control nor an intentionally excluded direct-engine test
may be silently counted as a passing required public test.

## Historical evidence and unresolved work

[G1](../evidence/E0031-8x4-physical-comparison/README.md) retains the rejected P
fanout result and qualified compact10 comparison. The later register-store
placement/routing failures, SRAM integration failures, [E0024](../evidence/E0024-mode0-pin-envelope/README.md)
attempts and scoped [E0028 held-program proof](../evidence/E0028-held-program-induction/README.md)
retain their own sources and assumptions. Earlier specifications describe
those checkpoints, not the current interface.

Analog rise/fall behavior, metastability/MTBF, broad peripheral interoperability,
unbounded continuous UART reception, an actual host transport adapter, FPGA
bring-up and fabricated-silicon observations remain outside the demonstrated
results. M0 owner teach-back remains pending regardless of engineering progress.

## Fresh G4 qualification checkpoint

<!-- G4 physical qualification from retained E0047 records -->
The [two complete G4 runs](../evidence/E0047-g4-submission-candidate/README.md),
qualified on 2026-11-14, discharge the physical requirements above at the same
frozen source `45c55f7cd95db2a883b0ffb5e864decd62d53601`. Each retains six original
archives, all ten prechecks and eighteen actual-netlist public groups, with
Windows/Linux audit replay and nine evidence-corruption controls rejected.
Both report +5.595886/+0.120791 ns setup/hold slack at 20 ns.
The flow has 85 configured entries, 77 executed top-level stages, 2 nested antenna stages and 8 frozen gate-disabled entries.
Recorded stage configuration/state bytes, netlists, timing/area and public
records agree. Only 764 bytes across 191 BGNLIB/BGNSTR timestamp records differ; all 995,697 GDS records have the same structure and all geometry records agree.
1,052 SPI, 1,160 I2C, 4 boundary and 36 abort records agree. UART comparison retains 97 RX/late-reader
landmarks; it is not a complete retained UART TX trace comparison.
G2 continuity remains separately identified. The [publication audit](../evidence/E0047-g4-submission-candidate/publication/README.md)
verifies stable v0.1.0, all 35 public assets, both original physical sets
replayed from downloads, platform-identical packages, standalone examples
and matching source/image identity. All nine tag workflows pass. Registry
manifest/config bytes and layer HEAD permissions/sizes were checked; this
does not claim a full pull of the newly published image.
