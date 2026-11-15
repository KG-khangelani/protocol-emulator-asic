# E0048 - Bounded G5 firmware-only waveform replay

Activated 2026-11-15; experiment qualified, publication pending. [D50](../../docs/decisions/0050-bounded-firmware-waveform-replay.md)
and the [acceptance contract](../../docs/specs/g5-waveform-replay.md) freeze one
use case, two control/fault programs, literal expected traces, 21 cases and a
sixteen-hour maximum investigation before execution. The independent review
confirmed the schedule arithmetic; that review is not execution evidence.

Baseline main: `d664a4c227762f4c62fbbb703eec245fda2a60a9`.
Unchanged qualified physical release: v0.1.0 at
`5bdc0e6b6449a829a5da1f8f9a8060257e974843`.
Runtime image to verify and use:
`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:a22fc6626bc4f61b52cd6a32793cec86f718f0943d078ad03cfbf8dc7932af88`.

No RTL, analog, silicon, new physical acceptance or owner-fluency result is
claimed. The original G1-G4 records, stable release and thirteen G3 programs
remain unchanged. Failed attempts will be retained rather than replaced.

The first native assembly attempt rejected the two leading `#` comment
markers: the existing assembler accepts `;`. No RTL ran. `assembly-rejection/`
retains both original sources, the actual failed result, frozen producing
source archive and CLI diagnostic. `amendment-01.json` prospectively changes
only those comment markers; the original declaration, every instruction,
expected pin trace, case and budget remain unchanged. The runner verifies
the correction byte for byte against the retained originals.

## Qualified result

[Original CI and replay](ci-66743b6/README.md) verify all 21 public cases in
each simulator, five expected rejections and byte-identical clean-clone
reproduction at committed source `66743b60b93508d2f00f23fa2cc2ac7db244bc3a`.
The actual trace moves only the selected rising edge by two clocks. Both
programs occupy 20 words / 80 bytes, and all twenty physical inputs remain
unchanged. The twelve checker tests and mandatory thirteen-example G3 guard
pass; native Windows produces the same eight compiled artifacts as Linux.
The original 310-file CI artifact, all 366 producing inputs and five rejected
rehashed evidence controls pass retained audit.

The [usable example](../../docs/waveform-replay.md) explains the pin ownership,
trigger/timeout behavior, timing assumptions and the value of replaying a
specific edge fault without adding hardware. This demonstrates a compact
additional use of the existing core; it does not establish a new architecture
or a minimum-size program. The verified software package and publication
checks remain to be completed before G5 closure.
