# G3 program toolchain contract

Status: acceptance defined before implementation, 2026-11-13. Target:
`od128-sram-v1`, qualified interface **0x22**, 128 logical 32-bit words.
G3 changes software and examples. The twenty D48-qualified physical inputs,
instruction semantics, G1/G2 evidence and owner-learning gates remain intact.

## Source and artifacts

A source begins with `.target od128-sram-v1`. Instructions use named operands;
labels denote word addresses. `.const NAME expression` defines integer symbols;
`.data TX0 expression` and `.data TX1 expression` initialize the two payload
registers (public addresses 1 and 4). `.idle expression` declares the byte of
external idle input levels for the two disabled synchronizer-flush edges.
Semicolon comments and blank lines are
ignored. Constants may reference earlier constants; instruction operands may
reference forward labels. Integer expressions support parentheses, addition,
subtraction, multiplication, floor division, shifts and bitwise operations.
No arbitrary Python execution, file inclusion or host-dependent expansion.

The assembler emits deterministic little-endian binary words, a JSON image,
a readable instruction/timing listing and an explicit public load/readback
transaction plan. Paths, timestamps and host platform do not affect generated
bytes. The JSON records source and binary hashes, format/target version, payloads,
labels, instruction fields, timing assumptions and any control-flow warnings.
An invalid source creates no output artifacts. Diagnostics identify source line
and the offending operand; duplicate/unknown fields and unused spellings fail.
No raw-word escape or implicit truncation hides invalid instructions.

## Instructions

The encodings come from the frozen D37 general engine and D42 SRAM revision.
Historical hand-assembled generators remain independent comparison inputs.

| Instruction | Named operands | Execution spacing to the following instruction |
|---|---|---|
| `SET` | `mask`, `value`, `oe` (bytes) | 1 accepted edge |
| `WAIT` | `cycles` (0..65535) | cycles + 1 |
| `HALT` | none | terminal after 1 edge |
| `WAIT_PIN` | `pin` (0..7), `level` (0/1), `timeout` (0..65535), optional `on_timeout=fault`, `skip` or label | 1..timeout + 1; final-edge match wins |
| `LOOP` | `count` (0..255), `end` (exclusive body-end label) | 1 edge dispatch, then count repetitions |
| `SHIFT_STEP` | `tx`, `rx`, `order=lsb/msb`, optional `drive=push_pull/open_drain`, `payload=TX0/TX1` | 1 accepted edge |
| `SHIFT_BURST` | `tx`, `rx`, `order=lsb/msb`, `period` (2..65535) | 8 * period; payload slots alternate |
| `DRIVE` | `tx`, `rx`, `order`, `mask`, `value`, optional `drive`, `payload` | 1 accepted edge |
| `SAMPLE` | `tx`, `rx`, `order`, `delay` (0..65535) | delay + 1; zero samples on its execution edge |

TX and RX must differ; DRIVE's auxiliary mask must exclude both. A LOOP body
contains 1..31 words, remains within the loaded program and cannot contain
nested LOOP, HALT or legacy timeout skip when its count is nonzero. General
WAIT_PIN failure branching abandons an active loop/partial shift as specified
in G2. Branch destinations must be loaded word addresses. Backward branches
are allowed but explicitly prevent claiming a finite total schedule. Per-line
durations are instruction costs, not a promise that malformed shift sequencing
will execute; runtime phase/pin/order checks remain authoritative.

The listing identifies loop bodies/repeats, success/failure destinations and
conditional timing. Fixed schedules can be expanded to accepted-edge positions;
input-dependent execution must expose its choices instead of inventing a single
latency. Disabled edges freeze execution; asynchronous input synchronizers keep
clocking. The 50 MHz setting is a target, not a measured maximum frequency.

## Public loading and examples

Reset, check interface 0x22, write each four-byte little-endian word through
eight-word banks, read every byte after a rising edge, commit the complete length,
initialize payloads, exit load mode and flush idle inputs for two disabled rising
edges. A bank selection invalidates the image: recommit only after final readback.
Do not drive the shared pins during loader reads; an external protocol target
must release them. Runtime reads use dedicated `uo_out` selectors and preserve
GPIO ownership. Stop on interface/readback mismatch before enabling execution.

Versioned examples cover UART TX and bounded RX, both bit orders of all four
held-input SPI modes, and I2C write/read/repeated-START transactions with NACK
and bounded timeout cleanup. UART framing/delivery/host-service limits, SPI
input-hold requirements and digital open-drain/pull-up/stretch assumptions are
part of each example's documented contract.

## Acceptance and falsification

1. Compare assembled example bytes with existing independently encoded G2
   programs and reviewed fixed word vectors. Reject bad symbols, operands,
   control flow, capacity and target versions with useful diagnostics. Check
   cross-platform deterministic files and actual command-line error behavior.
2. Run generated load/readback plans against actual production RTL on both
   simulators. Test bank boundaries, wrong interface/readback and reload. Observe
   public pins only; program words must come from assembled source files.
3. Check protocol traces with the existing independent frame/bus oracles.
   Include meaningful changed-program and adverse-input controls, preserve
   expected failures and compare both simulators' normalized trace records.
4. Reproduce from a clean committed checkout in the pinned workbench, retain
   commands, source/tool/artifact identities and results, and make the documented
   command the CI entry point. The hardware production guard must still pass.

No new physical run is needed for unchanged qualified hardware. A larger
compiler, hardware transport adapter, analog validation, fabricated-chip test
and final submission readiness are separate work, not implied by this goal.
