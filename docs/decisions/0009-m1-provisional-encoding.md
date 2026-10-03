# D9 - Use a provisional bounded M1 encoding and preload

Date: 2026-10-02. Status: encoding retained; constant preload superseded by D10.

Decision: the first SET/WAIT/HALT implementation uses 32-bit words, a 16-bit
WAIT count, a five-bit PC supporting a declared maximum of 16 program words,
and an internal four-word combinational preload. The preload exercises the
engine but is not post-fabrication programmability. The reusable engine accepts
an instruction plus validity signal so simulation can test other programs
without adding protocol-specific RTL.

Encoding:

| Opcode `[31:30]` | Instruction | Remaining fields |
|---|---|---|
| `00` | SET | `[29:24]=0`, mask `[23:16]`, OE `[15:8]`, value `[7:0]` |
| `01` | WAIT | `[29:16]=0`, unsigned count `[15:0]` |
| `10` | HALT | `[29:0]=0` |
| `11` | WAIT_PIN (extended by D11) | pin `[29:27]`, level `[26]`, `[25:16]=0`, timeout `[15:0]` |

Reserved-bit violations enter FAULT. Logical GPIO maps to `uio_out/uio_oe`;
`uo_out` exposes state and PC for this experiment. Inputs are not yet consumed.

Reason: this is wide enough to state atomic SET and bounded WAIT behavior
without prematurely optimizing encoding. It gives the hypothesis a falsifiable
simulation target while keeping the absent loader and input synchronization
visible.

Limit: word width, WAIT range, PC width, preload contents, and debug mapping are
provisional. D10 evaluates `P-RELOAD` in simulation and D11 adds a bounded
input-wait primitive. Program-memory area, the complete `K-INPUT-WAIT`
workload, protocol workloads, CMOS5L fit/timing, and silicon behavior remain
`NOT_EVALUATED`.
