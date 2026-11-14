# G4 candidate: complete official qualification

Run [43543626249](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543626249)
completed all three production workflow jobs successfully on 2026-11-14.
Source: `45c55f7cd95db2a883b0ffb5e864decd62d53601`, attempt 1.
This is the first of the two predeclared clean G4 runs under D49.

`result.json` reports `PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES`.
All six original archives pass their API sizes and SHA-256 digests; every
one of their 1729 file members is indexed in `zip-files.json`.
The sealed producer contains 84 exact files. The frozen production
guard verifies all twenty adopted physical inputs and their original G2 references.

| Check | Observed result |
|---|---|
| Configured construction/check stages | 85 |
| Executed top-level stages | 77 |
| Nested antenna substages | 2 |
| Frozen gate-disabled stages | 8 |
| Official prechecks | 10 passed; none skipped |
| Actual-netlist public groups | 18 passed; none of the required groups skipped |
| Setup / hold slack at 20 ns | 5.5958856909900625 / 0.12079138031701087 ns |
| Mapped total cells / standard-cell area | 4201 / 53089.7598 um2 |
| Routed standard cells / area | 4679 / 61294.1 um2 |
| Public records | 1,052 SPI; 1,160 I2C; 4 boundary; 36 abort |

The mapped total includes one SRAM macro; its area is unknown to the
synthesis report and is excluded from that mapped area. The physical macro
area is audited separately as 49,488.4992 um2.

All audited routing, antenna, DRC, LVS, power-grid, fanout, capacitance and
slew violation counts are zero. The actual producer/consumer logs bind the
submitted GDS/netlist, runtime/PDK identity and macro models.

Raw GDS SHA-256: `2ae494ddf48df9b8069968a7f3da8f379ee8f6a899891e7649d585e75a465a17`.
Netlist SHA-256: `2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e`.

Both retained replays return `PASS_RETAINED_COMPLETE_SRAM_QUALIFICATION`.
Windows runs all nine deliberate corruption controls; every corruption
is rejected with its expected error. Controls include rehashed semantic
changes to production identity, stage configuration/skip, power-port count,
required test execution and submitted netlist, plus incomplete workflow,
wrong archive digest and wrong job source.

The Linux replay ran in isolated [CI run 43554467650](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43554467650),
job `132324068684`, at source `7b73d99fbf300c1041aa930409ea63fc031d20f4`.
The runner pulled the previously verified public alpha.7 workbench image:
`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307`.
Its actual configuration/image ID was `sha256:6f45e71162641466c4e9e08601a383c8a081c06b263114903a181d5f8f971451`.
The replay used `--pull=never` and `--network=none`; its source checkout
was mounted read-only with a separate writable replay output directory.

The [common Linux proof](../linux-ci-43554467650/README.md) retains the
original 33-member archive `14098180180.zip`, completed job log, API
observations, frozen workflow/runner source and image inspection records.
`linux-ci-binding.json` binds this candidate to that original proof and
the three copied Linux members. Their bytes are unchanged, including the
compressed raw log. `invocation-linux.json` is the actual CI receipt.
The independent Windows invocation and all nine control records are
preserved unchanged. This record makes no claim of local Docker recovery.

From the repository root, use a fresh output directory:

```text
python evidence/E0047-g4-submission-candidate/ci-43543626249/verify.py --output build/g4-candidate-replay --controls
```

The replay reconstructs the original ZIPs, verifies every original member
and the sealed producer, and requires the full semantic audit result to
equal the retained record. It audits archived evidence rather than running
a new physical build. The independently dispatched second run and geometry
comparison are recorded separately by E0047.

Public netlist testing is functional zero-delay simulation. Seven UART
groups execute assertions; the retained comparison data contain 96 RX
landmarks and one late-reader landmark, not complete UART TX waveforms.
The fast model set combines -40 C standard cells and -55 C SRAM. These
results do not measure silicon, isothermal characterization or maximum clock frequency.

The optional rendering archive is outside this six-archive qualification.
`SHA256SUMS` covers every curated retained file except itself.
