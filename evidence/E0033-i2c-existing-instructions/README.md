# E0033 - Existing compact10 instruction and capacity baseline

Date: 2026-11-12. Goal: G2, following D36. Status: **scoped public kernels
measured on both simulators; full I2C remains unqualified**.

All five generated compact10 RTL hashes exactly match D35's qualified G1
candidate. Production RTL, the experimental candidate and physical settings
are unchanged. These tests use only public program/data loading, readback,
resolved pins and normal public execution status.

## Results

Icarus and Verilator each pass two groups and produce ten identical public
records, including trace hashes. Nine records exercise a released-SCL input
wait; the tenth measures a literal write schedule and real loader rejection.

| Case | Observed result |
|---|---|
| Unstretched, short stretch, penultimate and final observation edges | Ten-word program takes the event path and HALTs three clocks after observation |
| Raw high first observable after the deadline; permanently held SCL | Ten-word program releases both lines one clock after expiry and HALTs after two; within the frozen 16-clock bound |
| Same input wait inside a one-iteration LOOP, successful input | Seven-word program reaches HALT |
| WAIT_PIN timeout skip inside that LOOP | FAULT at the deadline, SDA remains driven low: expected cleanup failure |
| Plain WAIT_PIN without timeout skip | FAULT at the deadline, SDA remains driven low: expected cleanup failure |
| Literal SET/WAIT/WAIT_PIN write-wire schedule | 122 words / 3,904 program bits, versus actual 10 words / 320 bits; also exceeds the current 32-address PC range |
| Public commit of first invalid length, eleven | Real loader clears ready and holds execution/output disabled |

The fitting program uses zero-count LOOP as a short forward skip over an
inline two-instruction cleanup path. This is an existing general instruction,
not a new exception mechanism. Count 49,999 in WAIT_PIN, following the release
instruction, puts its final observation exactly 50,000 core clocks after
release. The two-register input latency and final-edge priority are observable
in the public traces. Pins stay open drain during the kernel.

The kernels deliberately omit I2C framing and are not accepted transactions.
The 122-word list covers a literal successful write-wire sequence, but has no
conditional ACK rejection, receive or timeout cleanup. It was counted, never
aliased into the loader or executed. It is not a global ISA lower bound and
does not establish an achieved bit rate. Its size motivates a better schedule
and measured instruction/storage comparison rather than claiming ten words
can accommodate the complete contract.

## Reproduce and inspect

Inside the locked workbench:

```sh
python3 experiments/i2c/run_baseline.py --output build/i2c-baseline/new-attempt
```

The output directory must be new. `result.json` retains commands, source hashes,
simulator identities and counts. `icarus/` and `verilator/` retain logs, JUnit,
program words and public event traces. The runner checks actual simulator names
from their logs, source stability and byte-identical records across simulators.
`validation.json` checks the generated source against G1's exact candidate.
`SHA256SUMS` covers the curated artifacts.

`initial-launch/` preserves the invalid first attempt. A command-substitution
mistake changed the SIM/SIM_BUILD option names, so both launches used Icarus
and shared a build path. Both confirmed running containers were stopped and
their partial results rejected. The corrected launcher passes explicit argument
lists, isolates builds and verifies the observed simulator identity. There is
no dual-simulator claim from that first attempt.

## Next experiment

Before adding instructions, test whether the existing SHIFT_STEP can receive
SDA while its all-zero transmit payload pulls SCL low on the capture edge.
This may avoid a separate receive operation; it is currently an untested
hypothesis. Then measure a complete branching/cleanup schedule and choose any
general instruction or storage change. No dedicated I2C RTL, combined protocol
qualification, fresh physical pass or owner-fluency promotion follows here.
