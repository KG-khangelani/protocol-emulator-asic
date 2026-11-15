# G5 acceptance contract - triggered irregular digital stimulus

Frozen before execution on 2026-11-15 under [D50](../decisions/0050-bounded-firmware-waveform-replay.md).
Question: can the existing program store and timed GPIO reproduce an irregular
three-wire stimulus, then move exactly one selected edge to recreate a timing
fault, without changing any hardware?

## Use and programs

A logic test fixture supplies a trigger on `uio[7]`. The chip drives stimulus
lines `uio[2:0]`; pins 3 through 7 remain inputs. All lines initially have value
zero. A host loads and reads back all 80 bytes through the documented public
interface 0x22, commits 20 words, and exits loading with two disabled edges to
flush the input synchronizer. External devices release the shared bus during
loader reads and never drive pins 0 through 2 during runtime.

The frozen [control](../../experiments/waveform_replay/control.asm) and
[timing fault](../../experiments/waveform_replay/timing_fault.asm) differ only
in two WAIT immediates. Word 0 drives three low outputs. Word 1 waits for a
high synchronized trigger, with timeout 32 and an absolute branch to the
shared cleanup at word 18. Word 19 halts. No payload, loop, receive or
protocol-specific operation is used.

The independent oracle consumes the literal table in `expected.json`; it must
not import the assembler, decode instructions or derive expectations from a
simulated trace. Relative edge zero is the first stimulus SET after trigger
acceptance. Every intervening edge must preserve the previous pin values.

| Relative rising edge | Control output byte | Fault output byte | Enable byte |
|---|---|---|---|
| 0 | 1 | 1 | 7 |
| 3 | 3 | 3 | 7 |
| 8 | 2 | 2 | 7 |
| 13 | 6 | 6 | 7 |
| 20 | 7 | 6 | 7 |
| 22 | 7 | 7 | 7 |
| 29 | 3 | 3 | 7 |
| 37 | 1 | 1 | 7 |
| 46 | 0 | 0 | 7 |
| 52 | 0 | 0 | 0 |
| 53 | 0 (HALT) | 0 (HALT) | 0 |

Thus only the pin-0 rising edge at 20 moves to 22; outputs differ only at
relative edges 20 and 21. Later transitions and termination are identical.
Internal PC/wait status may differ near the changed waits. The program
footprint is 20/128 words = 80 bytes = 15.625% of logical capacity. This is a
measured example, not a minimum-program-size proof.

## Timing and input limits

Runtime edge 1 executes word 0. With continuous enable, the trigger first high
at raw sampling edge N is consumed at N+2 and starts the waveform at N+3.
The normal N=8 case therefore starts at edge 11, releases at 63 and halts at
64. A trigger high throughout the two disabled flush edges starts at edge 3.
Raw edge 32 is the last accepted arrival: match at 34, first stimulus at 35,
release at 87, HALT at 88. Raw edge 33 is too late. Absent, wrong-pin, late or
unsampled input times out at 34, releases at 35 and halts at 36. Final-edge
match wins. WAIT_PIN observes a level, so an already-high input is accepted.

The clock period in simulation is 20 ns, matching the 50 MHz design target.
At that assumed rate the selected edge moves 40 ns and the waveform releases
after 1.04 microseconds from its first edge. These are digital schedule
conversions, not new Fmax, pad-delay, metastability, pulse-width, analog-glitch
or fabricated-chip measurements. Phase cases change the trigger 9 ns, 5 ns
or 1 ps before a sampling edge and hold it high thereafter. The simulator's
deterministic capture is not a physical setup/hold guarantee. A short pulse
entirely between samples must not trigger. Arbitrary asynchronous triggers
need external electrical/timing design and sufficiently held levels.

Enable must stay high for wall-clock timing. Two deliberately disabled runtime
edges must stretch the remaining trace by two clocks and be rejected against
the unpaused wall-clock schedule. Synchronizers continue while disabled.
HALT does not release pins: explicit cleanup is part of this program. Reset,
reload or other host intervention invalidates a running trace. The host and
fixture must obey [the published electrical assumptions](../submission.md#external-host-and-electrical-requirements).

## Frozen cases and measurements

`expected.json` freezes 21 uniquely named cases in three public test groups.
Fifteen waveform cases cover both programs at three trigger phases, already
high and final-allowed inputs, both no-trigger paths, late input, wrong input
pin and an unsampled pulse. Four waveform rejection controls use fault versus
control, an uncompensated delay, missing cleanup release and disabled-clock
stretching. Loader controls reject a corrupted readback before commit, then
show that a good reload recovers. Five cases expect rejection; rejection is
an expected experimental outcome, not a failed test runner.

Record every runtime rising edge (raw input, enable, output, output enable and
public status), all loader checks and eight post-HALT edges. Check the complete
trace, exact duration/trigger latency, no extra pin changes, ready/terminal
status and stable released pins. Record program bytes and footprint. Both
Icarus and Verilator must agree on all canonical records and trace bytes.
Repeat from a clean committed checkout in the immutable v0.1.0 workbench,
retain actual image/source identities and exact commands, and rerun the
existing G3 program qualification as a mandatory continuity guard.

Checker tests must reject changed/missing/duplicate edge records, wrong pin
ownership, extra post-HALT activity and incorrect fault compensation. Keep
failed attempts and original logs. Do not weaken this table to fit outputs.
If an expectation is wrong, record a prospective correction and the rejected
run before a fresh attempt; the budget does not restart.

## Stop and result

The investigation has a maximum sixteen elapsed hours from 2026-11-15 08:30
UTC (a conservative implementation of two eight-hour working days), including
preparation and CI waits. Stop by 2026-11-16 00:30 UTC or immediately on a
mandatory G1-G4 regression. A successful result keeps the example, independent
checker and reproducible evidence. Otherwise retain the negative finding and
defer further experiments. No new RTL, ISA extension, alternate substrate,
USB/Ethernet work or formal/physical rerun is justified by this experiment.
