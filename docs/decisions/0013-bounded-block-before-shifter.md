# D13 - Implement bounded blocks before a shifter

Date: 2026-10-03. Status: implemented candidate; local qualification passed.

Decision: evaluate K-BOUNDED-LOOP before K-SHIFT-8, using a non-nested LOOP
instruction with an 8-bit iteration count and immediate following body.

Reason: bounded repetition compresses timed SET/WAIT schedules shared by every
target protocol and needs only counter/start/end state. A useful bidirectional
shifter also requires unresolved payload loading, received-data readback,
direction and sampling-phase contracts. Combining those decisions now would
prevent attributing cost or failure to one capability.

The selected LOOP is encoded within opcode `01`: bit 29 is one, body length is
`[28:24]`, `[23:8]` are zero, and count is `[7:0]`. Count zero skips the body;
1..255 execute it exactly that many times. Nesting and control-flow exits from
an active body fail closed. See `../specs/k-bounded-loop.md`.

Limit: this does not reject a future shift datapath. It orders experiments so
the loop's program-size benefit and complete-chip state cost are measurable
before shift-specific state is introduced.
