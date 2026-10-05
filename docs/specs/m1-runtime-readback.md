# M1 nonintrusive public register readback

Status: locally verified simulation candidate, D18/E0018. Official top-level ports and loader
transactions remain unchanged. This read path is protocol-independent.

## Selection and ownership

With `ui_in[7:5]=3'b011`, `uo_out` exposes the data register selected by
`ui_in[4:0]`. In every other mode `uo_out={state,program_ready,pc}` as before.
The exact read values are:

| Address | Value on dedicated `uo_out` |
|---:|---|
| 1 | TX payload |
| 2 | most recently completed raw RX byte |
| 3 | `{7'b0,raw_rx_valid}` |
| 4 | alternate TX payload |
| 0, 5..31 | zero; address 0 is NOT the loader length register here |

Thus `ui_in=62` (hex) reads raw RX and `63` reads raw-valid. `ui_in=00`
returns execution status. Bit 6 is a read selector only when bit 7 is zero:
it MUST NOT write program/data, reset the engine, or qualify a clock edge.
Neither reading nor restoring status is an accepted execution operation.

All read values are combinational: a raw result/valid committed on rising edge
n is visible after that edge's combinational settling, with no extra edge.
There is no registered snapshot; data may change on any capture edge. A host
must allow pad propagation and meet its own sampling setup/hold requirements;
no physical access delay is established by simulation. Read selection can be
held across clocks while RUN, WAIT, HALT or FAULT, with either enable value.
When read-selected, status is temporarily hidden, not modified.

With bit 7 zero, `uio_out/uio_oe` remain the engine's GPIO value/direction in
ALL read/status modes. In particular this path cannot drive a released UART
RX pin. With bit 7 one the existing loader still owns all eight `uio` pins,
resets the engine on a sampled edge, and drives them all on a loader read.
Do not use loader reads while an external push-pull protocol source owns RX.

Chip reset is synchronous and wins over enable/read selection. A sampled reset
erases program/data and releases GPIO; selected data reads then return zero.
Enable freeze affects the executor, not this combinational read path or the
always-clocked input synchronizer. Runtime reads cannot restart terminal state.

## Verification obligations

Check the selector's exact decode, implemented/reserved register values,
same-edge RX visibility, and original status/loader behavior. Hold runtime
selection across real execution edges, including bit 6 high and a writable TX
address: prove absence of accidental writes/reset by public progression and
payload preservation. Check GPIO ownership while reading active input, HALT,
FAULT, disable and reset. Formal checks cover the new combinational top-level
decode/ownership/gating; end-to-end receive liveness remains a pin simulation
property, not a combined formal proof or physical result.
