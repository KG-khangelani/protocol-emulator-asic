# E0048 - Bounded G5 firmware-only waveform replay

Activated 2026-11-15; execution and qualification pending. [D50](../../docs/decisions/0050-bounded-firmware-waveform-replay.md)
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
