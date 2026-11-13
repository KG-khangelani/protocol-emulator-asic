# G3 program toolchain

The versioned assembler targets the unchanged D48-qualified SRAM core,
interface 0x22. Thirteen readable UART/SPI/I2C sources reproduce the preserved
independent G2 program words. No new instruction, protocol-specific RTL path
or physical-input change is introduced.

## Local implementation checks

`local/` retains the original dual-simulator run and Windows-generated files,
with every normalized public-pin trace and an archive-member hash map. Both
simulators pass four groups / 55 cases, including 15 expected rejections, and
all records are identical. The 53 deterministic program artifacts match byte
for byte between Windows and the pinned Linux workbench. Twenty assembler
acceptance tests and the complete 147-test repository check pass.

The controls cover full-bank loading/readback and reload, mismatched interface
and program readback, wrong UART period, framing fault/host quarantine, all
eight SPI edge-only failures, a wrong SPI sample delay, active-high I2C and an
incorrect I2C timeout. The positive I2C cases include NACK, stretching, bounded
cleanup and the last accepted/first rejected timeout boundary.

These are local working-tree checks retained with the implementation commit;
their original raw input hashes and source baseline are inside the archive.
The hardware guard passes all twenty unchanged physical inputs. G2's physical
evidence, UART/SPI/I2C scope limits and separate owner-fluency status remain.

Reproduce with `tools/workbench.ps1 ProgramTest` on Windows or
`tools/workbench.sh ProgramTest` on Linux. See [the guide](../../docs/programming.md)
for building a source file, reading its schedule and following the public
load/readback/run plan. No hardware transport adapter or fabricated-chip
result is claimed.

## Clean checkout and CI qualification

[`ci-0297655/`](ci-0297655/README.md) retains original Windows/Linux
run43393826878 at committed source `0297655e22ded931baae483b6deff81b7c9ccffd`.
Both jobs pass. A separate `git clone --no-hardlinks` on H: starts and ends
clean and passes the same pinned-workbench command. All 55 public cases,
15 expected rejections, normalized traces and 53 generated artifacts agree.
The frozen audit verifies every original archive member, all 351 committed
producing inputs, actual image identity, job logs and independent clone records.
Its replay exactly reproduces the retained verification report.

All four G3 engineering checks are satisfied. The [release tools](release-tools/README.md)
produce alpha.7's standalone assembler/examples package and untouched original
CI ZIPs. Windows and Linux create identical five-file packages; the extracted
standalone distribution rebuilds all thirteen examples and rejects an invalid
target without creating output.

## Verified publication and completion

[Alpha.7](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0-alpha.7)
uses source `33e5e9b286d63317c24eec85ffb0d9ea75f0f8ad`.
The [publication audit](publication/README.md) verifies all 23 anonymous asset
downloads, both checksum lists and all 73 toolchain ZIP members. Its eighteen
source files match committed Git bytes, and its 53 compiled files match original
Windows/Linux CI and the clean clone. Both original CI ZIPs are unchanged.
The original publication archive's 1,948 members and all 351 producing inputs
pass semantic/source audit, including eight production stages, two 147-test
executions and preserved historical SPI gates. All nine tag workflows / 22 jobs pass.

The published Linux amd64 image's source/version labels and actual tested
configuration match the release; both version and commit tags resolve to the
same digest. Anonymous layer HEAD requests verify read access and declared size;
layer bodies are not downloaded. The immutable image is:

`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307`

[The completion audit](completion-audit.json) closes G3 on 2026-11-13.
The twenty qualified hardware inputs and original alpha.6 physical adoption
remain unchanged. G4 submission readiness and owner fluency remain separate.
