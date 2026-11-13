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
Clean committed checkout and CI qualification remain the next G3 gate. The
hardware guard passes all twenty unchanged physical inputs. G2's physical
evidence, UART/SPI/I2C scope limits and separate owner-fluency status remain.

Reproduce with `tools/workbench.ps1 ProgramTest` on Windows or
`tools/workbench.sh ProgramTest` on Linux. See [the guide](../../docs/programming.md)
for building a source file, reading its schedule and following the public
load/readback/run plan. No hardware transport adapter or fabricated-chip
result is claimed.
