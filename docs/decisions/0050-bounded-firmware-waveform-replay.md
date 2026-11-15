# D50 - Test triggered waveform replay without changing the chip

Date: 2026-11-15. Status: accepted for one bounded G5 experiment.

G4 has closed the physical and publication gates. Use its unchanged
`od128-sram-v1` substrate as a small triggered digital stimulus source for
reproducing a relative-edge timing fault. This is one use case beyond the
UART/SPI/I2C workloads that shaped the design, not a claim of a new ISA or a
general waveform instrument.

Freeze two twenty-word programs and a literal expected pin schedule before
execution. The fault program delays one rising edge by two clocks and
compensates the following wait, preserving every later output transition.
An independent checker must reject the fault against the control schedule,
uncompensated timing changes and omitted pin release. Public loading/readback,
trigger phase/boundary cases, timeout cleanup and both RTL simulators are
required. Preserve the thirteen G3 examples and all twenty qualified physical
inputs. No new RTL or physical-flow claim is permitted.

The [contract](../specs/g5-waveform-replay.md) and its literal
[expectations](../../experiments/waveform_replay/expected.json) define the
experiment. Its total allowance is two eight-hour working days. We apply the
stricter continuous sixteen-hour cap from 2026-11-15 08:30 UTC, including
preparation, parallel work and CI waits: stop by 2026-11-16 00:30 UTC.
Do not extend the budget by resetting a run or changing tools. Retain a negative
result if the acceptance criteria cannot be met, or stop immediately if a
mandatory G1-G4 gate regresses. G6 and actual entry submission remain separate.

E0048 will retain original observations, failures, runtime/source identities
and reproduction. A useful qualified result may be published as an additive
software milestone; stable v0.1.0 and its physical evidence remain immutable.
