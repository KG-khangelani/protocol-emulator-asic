# Submission packet

Updated 2026-11-14. **G4 is complete: physical reproduction, software distribution, stable release and matching workbench are verified.**

<!-- G4 physical qualification from retained E0047 records -->
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
| Verified release | [v0.1.0](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.0), source `5bdc0e6b6449a829a5da1f8f9a8060257e974843`; [publication audit](../evidence/E0047-g4-submission-candidate/publication/README.md) |
| Workbench package | [Public container package](https://github.com/KG-khangelani/protocol-emulator-asic/pkgs/container/protocol-emulator-asic-workbench); `ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:a22fc6626bc4f61b52cd6a32793cec86f718f0943d078ad03cfbf8dc7932af88` |

The final documentation/release revision can follow the physical producer
revision. E0047 verifies all twenty frozen physical inputs and the reviewed program
bytes against the release commit; the publication audit binds those
identities to the actual public downloads.

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
| Tiny Tapeout GDS and precheck | [Production workflow](../.github/workflows/gds.yaml), [fresh G4 qualification](../evidence/E0047-g4-submission-candidate/README.md) | Both runs pass every required physical, precheck and public-netlist gate; original archives and frozen replays are retained. |
| Architecture and instruction set | [Architecture](architecture.md), [ISA](isa.md), [Tiny Tapeout datasheet](info.md) | Check the guides against the frozen implementation. |
| Programming tools and examples | [Assembler](../tools/assembler.py), [programming guide](programming.md), [thirteen examples](../programs/od128-sram-v1/README.md) | Verify clean CI, standalone distribution and deterministic packaging. |
| Verification approach | [Verification guide](verification.md), [research ledger](research-ledger.md), [evidence index](../evidence/README.md) | Retain original archives, frozen replay and failed controls. |
| Description of AI use | [AI-use account](ai-use.md) | Preserve a candid account of assistance and independent-check limits. |

Gate-level simulation is recommended in the FAQ and is a required project
gate. Both fresh runs execute the actual submitted netlist. They were registered
before interpretation and use separate clean checkouts of the same frozen source.

| Role | Official run | Retained qualification |
|---|---|---|
| Candidate | [43543626249](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543626249) | [Complete audit](../evidence/E0047-g4-submission-candidate/ci-43543626249/README.md): 6 original ZIPs, 10 prechecks, 18 public-netlist groups, Windows/Linux replay and 9 rejected corruptions. |
| Reproduction | [43543629839](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543629839) | [Complete audit](../evidence/E0047-g4-submission-candidate/ci-43543629839/README.md): 6 original ZIPs, 10 prechecks, 18 public-netlist groups, Windows/Linux replay and 9 rejected corruptions. |

Each reports +5.595886/+0.120791 ns setup/hold slack at 20 ns and
61,294.1 square micrometres of routed standard-cell area, separate from SRAM.
Only 764 bytes across 191 BGNLIB/BGNSTR timestamp records differ; all 995,697 GDS records have the same structure and all geometry records agree.
Netlist, timing/area, recorded stage states and public observations agree.
The flow has 85 configured entries, 77 executed top-level stages, 2 nested antenna stages and 8 frozen gate-disabled entries.
See the [reproduction record](../evidence/E0047-g4-submission-candidate/reproduction.json).

G2 continuity is recorded separately: its original geometry agrees after
timestamp normalization, with matching netlist, physical inputs, metrics
and public records. Its historical qualification and adoption are preserved.

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
physical qualification directory describes its exact replay command and scope.
The reproduction helper compares both original layouts and the separate G2
reference after those retained audits have run.

<!-- G4 publication closure from retained evidence -->
Publication is verified for stable `v0.1.0` at release source `5bdc0e6b6449a829a5da1f8f9a8060257e974843`. All 35 public assets, 435 bundle members and the matching workbench image/source identities pass; all nine tag workflows / 22 jobs pass. Windows and Linux produce 17 byte-identical assets, and the standalone bundle rebuilds all thirteen examples into 52 identical files. See the [publication audit](../evidence/E0047-g4-submission-candidate/publication/README.md) and [completion audit](../evidence/E0047-g4-submission-candidate/completion-audit.json).

The official page was rechecked on 2026-11-14 with unchanged content and no
final form. Recheck it again before entry. When the final form appears,
the repository, final release and this write-up provide the prepared material.
Submitting that entry is separate. G5 experiments and G6's owner teach-back
remain outside this engineering completion.
