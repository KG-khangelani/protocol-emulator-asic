<!-- Updated 2026-11-14: qualified SRAM production and G3 programming interface. -->
## How it works

A reloadable temporal engine implements UART, SPI and I2C through programs on
the same circuit. The current interface is **0x22** (`od128-sram-v1`): 128
logical 32-bit program words backed by one 256-by-32 IHP SRAM macro, with 353
register bits for execution, valid-word tracking, fetch and other state.
There are no separate UART/SPI/I2C protocol controllers.

Generic operations set GPIO values/directions, count clock edges, wait for
synchronized input levels with bounded timeout/branching, repeat counted blocks
and shift/sample bits. Open-drain drive releases a line for one and pulls it
low for zero. SPI clock/select and I2C framing/ACK/cleanup are programmed.
The assembler emits binaries, decoded JSON, timing listings and public loading
plans; thirteen versioned examples are in `programs/od128-sram-v1/`.

Reset is synchronous and active-low: hold `rst_n=0` through a rising edge.
It wins over enable, releases GPIO outputs and invalidates the loaded image.
The SRAM has no reset; valid-word tracking makes unwritten words read as zero.
Reset or board power-down on deselection requires reloading before useful execution. With reset
released, `ena=0` freezes execution while input synchronizers keep clocking.
Each input passes through two clocked stages; this digital model does not
establish analog metastability performance.

## How to test

Use `tools/workbench.ps1 Programs` to build the examples and `ProgramTest` to
load/read/check them in both simulators. Linux uses `tools/workbench.sh` with
the same actions. `docs/programming.md` gives the commands and exact plan.
The plan represents public pins; a fabricated-board transport adapter is not
included and no fabricated-device test is claimed.

During loading, the external protocol partner must release the shared bus.
Check `ui_in=0x67` returns `uo_out=0x22`. Select eight-word banks 0..15 at
register 5 (`ui_in=0xE5`), then write four little-endian bytes per word with
`ui_in=0xC0 | offset`, where offset is 0..31 within that bank. Writes require
reset released and enable high; the host drives `uio_in` for writes.

Read each program byte with `ui_in=0x80 | offset`, releasing all host drivers.
Hold the address through a rising edge and sample the chip's `uio_out` after
settling. Interface 0x22 program readback needs that edge, with either enable
value. Bank selection invalidates readiness; after all readback passes, commit
the complete length 1..128 at register 0 (`ui_in=0xE0`). This restores bank
zero. Initialize payload registers 1 and 4 as the program requests.

Exit loader mode with `ui_in=0x00`, present the example's external idle levels,
and allow two rising edges with enable low. Set enable high: word zero executes
on the next rising edge. Stop on any interface/readback mismatch. Entering
loader mode resets execution; it is not nonintrusive runtime observation.

Ordinary `uo_out` reports state in bits 7:6, ready in bit 5 and the low five PC
bits in 4:0. Dedicated runtime reads preserve GPIO ownership: select `0x62`
for raw RX, `0x63` for raw-valid, `0x66` for full PC and `0x67` for interface
identity. Raw-valid is not framing acceptance or a receive queue.

## Protocol and external-hardware limits

UART TX and bounded two-frame RX, all four SPI modes in both bit orders, and
Standard-mode I2C write/read/repeated-START transactions are qualified within
their documented digital contracts. UART RX needs host service and discards a
faulty/interrupted batch; it is not continuous autonomous lossless reception.
SPI requires its declared input-hold profile. I2C uses an external resolved
open-drain bus with suitable pull-ups and bounded stretching/timeout cleanup.

Example pin assignments and timing premises are in the example README and
`docs/programming.md`. Check board voltage compatibility, pull-ups, level
shifting, settling and clock/reset requirements before connecting equipment.
Do not drive shared pins against the chip during loader readback.

G2/E0045 qualifies the exact production files with 8x4 CMOS5L GDS, positive
setup/hold slack at the 20 ns target, ten prechecks and eighteen actual-netlist
public groups. G3/E0046 qualifies the readable toolchain. G4/E0047 is performing
fresh final qualification and reproduction. The 50 MHz flow setting is not
measured Fmax or a board-I/O/analog guarantee. FPGA, fabricated-silicon and
unrestricted peripheral-interoperability results remain absent.
