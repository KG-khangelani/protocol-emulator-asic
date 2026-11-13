# Assemble, load and inspect a program

The chip runs a program loaded through its public pins. G3's small assembler
turns readable instructions into the exact 32-bit words used by the qualified
G2 core. It also produces a timing listing and a step-by-step loading plan.
The supported target is **od128-sram-v1**, interface **0x22**, with 128 words.

## Build and test the examples

From a clean checkout on Windows with Docker running:

```powershell
.\tools\workbench.ps1 Programs
.\tools\workbench.ps1 ProgramTest
```

On Linux:

```sh
./tools/workbench.sh Programs
./tools/workbench.sh ProgramTest
```

The wrappers use the repository's locked workbench. Each command creates a fresh
directory under `build/programs/` and prints its path. `Programs` only assembles
and checks the frozen reference words. `ProgramTest` also checks the tools,
runs assembler acceptance tests, executes the generated public loading plans
and protocol programs in Icarus and Verilator, and compares their complete
normalized observations. The tests use the actual production `src/` files and
the hash-checked digital SRAM models. A failed run is retained separately.

Inside the workbench, use an explicit new directory when retaining a run:

```sh
python3 tools/run_program_examples.py --out build/my-program-check
```

The [versioned examples](../programs/od128-sram-v1/README.md) cover UART TX and
bounded RX, eight SPI mode/order combinations and three I2C transactions.
Their catalog contains independently encoded G2 words; byte drift stops the
build. This command simulates the public interface; it does not connect a host
adapter to fabricated hardware.

## Write a small program

```text
.target od128-sram-v1
.const DELAY 99
.idle 0
entry:
    LOOP count=3 end=done
    SET mask=1 value=1 oe=1
    WAIT cycles=DELAY
    SET mask=1 value=0 oe=1
    WAIT cycles=DELAY
done:
    HALT
```

Save it as `blink.asm`, then assemble it with Python 3.11 or newer. This step
uses only Python's standard library and also works on Windows:

```sh
python tools/assembler.py blink.asm --out build/blink-01
```

The output directory contains:

| File | Purpose |
|---|---|
| `program.bin` | Four little-endian bytes per word; no hidden header |
| `program.json` | Version, source/binary hashes, payloads, labels, decoded instructions and schedule |
| `program.lst` | Words beside readable instructions, execution spacing, loop counts and conditional branches |
| `load-plan.json` | Public signal values, pin ownership and expected readback for each clocked step |

Use a new output directory for each build. An invalid program creates no output
and reports its source line. An existing directory is preserved. Constants and
labels avoid manual address counting; unknown fields, reserved encodings,
invalid loop bodies and programs above 128 words fail before loading.
See the [complete syntax and acceptance contract](specs/g3-program-toolchain.md).

## Read the timing listing

An accepted edge is a rising clock with reset released and enable asserted.
`WAIT cycles=99` makes the next instruction execute 100 accepted edges later.
`SHIFT_BURST period=434` occupies eight bit periods. A LOOP is one dispatch edge
followed by its body repeated exactly `count` times, with no extra loop-back edge.
The example above halts on accepted edge 608: one LOOP, three 202-edge bodies,
then HALT. A disabled clock edge does not consume an instruction or a wait.

For fixed dispatch, the listing shows each instruction's first/last execution
edge and execution count. These positions assume valid runtime shift sequencing,
continuous enable and no reset. A `WAIT_PIN` depends on synchronized external
inputs, so listing expansion stops at that decision and shows per-instruction
bounds and branch targets. A backward failure branch warns that finite total
runtime has not been established. The listing never turns an input-dependent
wait into a guaranteed single latency. The 50 MHz setting is the qualified flow
target, not a measured maximum frequency or a board timing guarantee.

## Follow the public loading plan

Every plan step holds the listed inputs through one rising clock and checks
the expected outputs after settling. Stop on the first mismatch. The plan ends
with execution disabled; its `run` record describes the next accepted edge.

1. Sample reset low with enable low. Release reset and select `ui_in=67` hex;
   dedicated `uo_out` must report interface `22` hex before any write.
2. Select each eight-word bank with `ui_in=E5` hex. Write each little-endian byte
   with `ui_in=C0 | (byte_offset % 32)` and the byte on `uio_in`. Writes require
   enable high; the chip releases its shared pins during writes.
3. Reselect banks and read with `ui_in=80 | (byte_offset % 32)`. Release the host's
   shared-pin drivers, hold the address through a rising edge, and compare the
   returned `uio_out` byte. Program readback is clocked on interface 0x22.
4. After all readback succeeds, write the complete length to `ui_in=E0` hex.
   This restores bank zero and marks the program ready. Every bank selection
   invalidates the image, so reading another bank afterward requires recommit.
5. Initialize and check payloads through registers 1 and 4 (`E1`/`E4` writes,
   `A1`/`A4` reads). The `.data TX0` and `.data TX1` declarations specify them.
6. Exit load mode with `ui_in=00`, present the declared external idle levels,
   and take two rising edges with enable low to flush the input synchronizer.
   Then set enable high; the next rising edge executes word zero.

An external protocol target must release the shared pins during loader reads,
when the chip drives all eight. The `.idle` value describes the attached input
environment during the two disabled edges; it is not a request to drive against
an external source. Pad settling and board setup/hold requirements still apply.

While running, use dedicated `uo_out` reads: `ui_in=62` for raw RX, `63` for
raw-valid, `66` for the full PC and `67` for interface identity (all hex).
`ui_in=00` restores ordinary execution status. These reads preserve GPIO
ownership. Entering loader mode resets the engine; use runtime reads during an
active protocol. Raw-valid is not a framing result or a receive queue. UART
host-service/framing limits, SPI input hold and I2C electrical assumptions are
documented with the examples and remain part of their acceptance criteria.

## Change an example deliberately

For experimentation, copy an `.asm` file and assemble the copy into a new build
directory. The standalone assembler accepts valid programs; the example catalog
additionally pins the reviewed program bytes. Do not regenerate the catalog to
hide a changed schedule. A public example update needs a version and migration
note, plus repeated independent trace checks. A hardware or instruction change
also needs explicit requalification under the production guard.
