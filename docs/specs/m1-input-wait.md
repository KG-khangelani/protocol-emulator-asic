# M1 synchronized input and bounded WAIT_PIN contract

Status: implemented candidate. `uio_in[7:0]` passes through two serially
connected sampling registers clocked on every rising edge while reset is
released. The engine consumes only the second-stage value on accepted edges.
If an external level is stable before edge 1, stage one captures it at edge 1,
stage two changes after edge 2, and the engine can act on it at edge 3. This is
a deterministic digital latency model, not an analog metastability proof.

`WAIT_PIN(pin, level, timeout)` uses opcode `11`, pin `[29:27]`, expected level
`[26]`, timeout action `[25]`, reserved bits `[24:16]=0`, and unsigned timeout
`[15:0]`. Timeout action zero enters FAULT; one advances PC by two so a program
can distinguish timeout from the normal event advance by one.

- If the synchronized pin already matches on the execution edge, advance PC.
- If it does not match and timeout is zero, enter sticky FAULT at that PC.
- Otherwise latch pin/level, enter WAIT, and set `wait_left=timeout`.
- On later accepted edges, a matching synchronized input wins and advances PC.
- Without a match, `wait_left>1` decrements. At `wait_left=1`, timeout action
  zero enters sticky FAULT and action one clears the wait and advances PC by two.
- Disabled edges do not consume timeout. Reset aborts the wait and clears both
synchronizer stages, engine state, and latched wait controls.

The loader and external-input path share `uio_in`. Loader bytes therefore pass
through the synchronizer. Before starting an input-dependent program, the host
must leave load mode, drive the intended idle input levels, and hold `ena=0`
for two rising edges. The synchronizer advances during those edges while the
engine remains at PC zero. This is a required loader-to-execution handoff, not
an assumption that loader data happens to resemble idle input.

Thus timeout is the exact maximum number of subsequent accepted observation
edges. A match on the final allowed edge succeeds. GPIO value/direction and PC
hold throughout a pending wait and on timeout FAULT.
