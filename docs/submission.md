# Submission packet

Updated 2026-11-14. **G4 qualification and publication are in progress.**
This packet collects the design, software and evidence for the Jane Street
Protocol Emulator ASIC competition. No competition entry has been submitted.
The completion decision belongs to [E0047](../evidence/E0047-g4-submission-candidate/README.md)
and the five checks in [G4](goals.md#g4---close-and-publish-the-final-design).

## Entry information

| Field | Prepared material |
|---|---|
| Project | Protocol Emulator ASIC |
| Public repository | [KG-khangelani/protocol-emulator-asic](https://github.com/KG-khangelani/protocol-emulator-asic) |
| Current production interface | `od128-sram-v1`, runtime identity `0x22` |
| Physical allocation | IHP CMOS5L, 8x4 Tiny Tapeout tiles, 20 ns clock target |
| Frozen G4 physical source | [`45c55f7cd95db2a883b0ffb5e864decd62d53601`](https://github.com/KG-khangelani/protocol-emulator-asic/tree/45c55f7cd95db2a883b0ffb5e864decd62d53601) |
| Final release | Intended tag `v0.1.0`; not yet published or verified. [Published releases](https://github.com/KG-khangelani/protocol-emulator-asic/releases) retain G1-G3. |
| Workbench package | [Public container package](https://github.com/KG-khangelani/protocol-emulator-asic/pkgs/container/protocol-emulator-asic-workbench); final image digest will be bound to the release publication record. |

The final documentation/release revision can follow the physical producer
revision. E0047 must establish that all twenty frozen physical inputs and the
reviewed program bytes remain unchanged; a later commit hash alone does not
establish that relationship.

## Design description

One reloadable temporal engine expresses UART, SPI and I2C through ordinary
programs. The same datapath sets GPIO values and directions, counts accepted
clock edges, waits for synchronized input levels, repeats bounded blocks and
shifts bytes. A general timeout branch abandons an incomplete operation so
firmware can perform cleanup. Open-drain output is a serial drive option.
The RTL contains no separate UART, SPI or I2C controller.

The production chip exposes 128 logical 32-bit words in one 256-by-32 SRAM
macro, alongside 353 register bits. SRAM and next-address prefetch made the
larger program store physically viable while preserving the selected
instruction schedules. Public loading and clocked readback let a host verify
the complete image before execution. The versioned assembler emits machine
bytes, decoded JSON, timing listings and a pin-level loading plan.

Thirteen readable examples cover UART transmit and bounded two-frame receive,
all four SPI modes in both bit orders, and I2C write, read and repeated-START
transactions. They use G2's reviewed machine words. This demonstrates useful
reprogramming on one core; it does not establish the smallest possible ISA or
support for every peripheral. See the [architecture](architecture.md),
[instruction set](isa.md), [programming guide](programming.md) and
[example catalog](../programs/od128-sram-v1/README.md).

The design process retained losing alternatives. G1's timed-GPIO P candidate
reduced routed standard-cell area but failed its fanout limit. G2's larger
register-backed stores failed placement or routing; the SRAM approach passed
the original physical gates. Those decisions and failures remain in
[D35](decisions/0035-select-compact10-physical-pilot.md),
[E0036](../evidence/E0036-g2-store-and-ci/README.md),
[E0042](../evidence/E0042-sram-prefetch-screen/README.md) and
[E0045](../evidence/E0045-g2-sram-qualification/README.md).

## Material for review

The [official rules and FAQ](https://blog.janestreet.com/protocol-emulator-asic-competition/)
were checked on 2026-11-14. They specify a January 18, 2027 deadline and 8x4
CMOS5L allocation. SRAM is permitted if the design fits and passes precheck.
The final submission form is still forthcoming. A video and FPGA demonstration
are optional, and no fixed clock or protocol speed is required. The dated
[rule observation](../evidence/E0047-g4-submission-candidate/rules-observation.json)
records this review.

| Published requirement | Repository material | G4 closure condition |
|---|---|---|
| Public source, RTL and tests | [RTL](../src/), [tests](../test/), [license](../LICENSE), [programming tools](programming.md) | Verify the final public source and download identities. |
| Tiny Tapeout GDS and precheck | [Production workflow](../.github/workflows/gds.yaml), [G2 qualification](../evidence/E0045-g2-sram-qualification/ci-94a3082/README.md) | Audit both fresh G4 runs, including all physical and precheck gates. |
| Architecture and instruction set | [Architecture](architecture.md), [ISA](isa.md), [Tiny Tapeout datasheet](info.md) | Check the guides against the frozen implementation. |
| Programming tools and examples | [Assembler](../tools/assembler.py), [programming guide](programming.md), [thirteen examples](../programs/od128-sram-v1/README.md) | Verify clean CI, standalone distribution and deterministic packaging. |
| Verification approach | [Verification guide](verification.md), [research ledger](research-ledger.md), [evidence index](../evidence/README.md) | Retain original archives, frozen replay and failed controls. |
| Description of AI use | [AI-use account](ai-use.md) | Preserve a candid account of assistance and independent-check limits. |

Gate-level simulation is recommended in the FAQ and is a required project
gate. Both G4 runs must execute the actual submitted netlist. These two runs
were registered before interpretation and are separate fresh checkouts of the
same physical producer revision:

| Role | Official run | Evidence status at packet preparation |
|---|---|---|
| Candidate qualification | [43543626249](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543626249) | Results not yet audited. |
| Independent reproduction | [43543629839](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543629839) | Results not yet audited. |

E0047 must retain all six original archives per run and compare actual source,
macro views, netlists, geometry, timing/area and public observations. GDS
timestamp differences may be separated from geometry differences. A successful
workflow badge alone is insufficient. G2's existing positive setup/hold slack,
ten passing prechecks and eighteen passing public-netlist groups remain
historical evidence, not a substitute for these fresh G4 results.

## External host and electrical requirements

The official FAQ describes 3.3 V demo-board I/O and permits external pull-ups,
transceivers and level shifting. Match the attached hardware to those I/O
levels; the chip's internal timing results do not qualify board voltage,
pad settling, pull-up sizing, bus capacitance or cable behavior.

The host supplies a continuous clock, holds active-low reset through a rising
edge and loads the program after reset or board power-down. Plain `ena=0` freezes
execution; it is not the board power-down operation. The host owns the loader
control inputs and drives shared pins only for writes. For readback, it releases
all eight shared pins while the chip drives them. Isolate the protocol partner
during loading, reconnect the declared idle environment and provide two disabled
flush edges before execution. No physical host adapter is included.

| Workload | Demonstrated digital boundary |
|---|---|
| UART | The examples use 434 accepted edges per bit, approximately 115,207 baud at the 50 MHz target. RX is a bounded two-frame batch with one raw-result register. Host service must meet `H >= 1`, `L >= 1`, `H + L <= 10P`; acceptance waits for framing validation and successful terminal state. Raw-valid is not a frame verdict or FIFO. See the [host-service contract](specs/p-uart-rx-host-service.md). |
| SPI | The examples use a 25-edge half-period and both bit orders in modes 0-3. MISO must satisfy the declared held-response envelope; edge-only responses are deliberate failing controls. See the [SPI contract](specs/p-spi-host-4mode.md). |
| I2C | One controller uses open-drain SCL/SDA with external pull-ups. The qualified write/read/repeated-START cases include ACK/NACK, stretching and bounded timeout cleanup under the [digital Standard-mode contract](specs/p-i2c-controller-100k.md). Analog rise/fall behavior and broad peripheral interoperability are untested. |

The 50 MHz clock is the qualified physical-flow target, not measured Fmax.
Netlist tests are functional zero-delay simulation; routed timing is a separate
analysis. The fast model set combines -40 C standard cells and -55 C SRAM.
There is no fabricated-silicon or FPGA result, analog-bus qualification,
continuous autonomous UART guarantee or owner-fluency pass.

## Reproduce and finish the packet

From the selected release checkout, with Docker running, use the locked
workbench commands described in the [verification](verification.md) and
[programming](programming.md) guides:

```powershell
.\tools\workbench.ps1 All
.\tools\workbench.ps1 Evidence
.\tools\workbench.ps1 Programs
.\tools\workbench.ps1 ProgramTest
```

Linux uses `./tools/workbench.sh` with the same action names. Each retained
evidence directory describes its own replay command and scope; use E0047's
final commands when its physical and publication audits are complete.

Before G4 closure, replace the pending entries above with verified run,
release and image identities and link the completion audit. Recheck the
official page for changed requirements. When the final form appears, the
repository, final release and this write-up provide the prepared material.
Submitting that entry is a separate action. G5 experiments and G6's owner
teach-back remain outside this engineering completion.
