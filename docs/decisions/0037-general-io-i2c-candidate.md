# D37 - Advance the general open-drain candidate to the remaining G2 gates

Date: 2026-11-12. Goal: G2. Status: **experimental direction; no production promotion**.

## Decision

Advance `od128`, which combines general bounded failure branching, a real
128-word store and optional open-drain/alternate-payload serial output. Retain
`literal255` as the measured control. Neither design contains an I2C opcode or
dedicated I2C controller. D35's qualified compact10 remains the historical
physical baseline; this decision does not replace its qualification.

E0033 demonstrated the cleanup and capacity limits before these changes;
E0034 demonstrated that existing shifting already receives SDA. The frozen
D36 acceptance checker was not changed to accommodate either candidate.

| Complete program | literal255 words | od128 words |
|---|---:|---:|
| Address and one-byte write | 136 | 54 |
| Address and one-byte read | 93 | 53 |
| Write, repeated START and read | 211 | 96 |
| Actually allocated program bits | 8,160 | 4,096 |

These are complete experimental images, including ACK rejection, STOP,
timeout cleanup and terminal markers. They are not instruction-set minima.
Both real stores include banked loading, readback and reset; no abstract
instruction list substitutes for actual storage cost.

## Observed behavior

Both simulators agree on all 1,160 od128 I2C records: 1,154 accepted protocol
outcomes and six required rejections. The matrix covers all bytes across the
three transaction kinds, ordinary addresses, four assigned response phases,
NACK locations, stretching at every release, and both sides of each final
observation edge. It is not the full Cartesian product of all parameters.
Nominal clock rates remain below the 100 kHz ceiling; exact rates are retained.

On the same pre-cleanup RTL, both simulators pass the twelve existing public
kernel/UART/SPI groups. All 1,052 SPI records equal the retained compact10
expectations, including four expected input-hold failures. UART framing,
last-byte delivery and host-service limits remain unchanged. This does not
establish continuous autonomous receive delivery or broader SPI compatibility.

The current cleanup is functionally equivalent to that measured RTL: Yosys
proves both engines equivalent, top connections differ only in whitespace,
data/synchronizer files are identical, and all 256 values prove the literal
store's redundant length ceiling removable. Current public boundary checks
pass both simulators. The current od128 and the equivalent literal candidate
also pass the 32-case I2C smoke. Scoped instruction induction, reachable covers
and two inspected counterexamples pass. Final-result assertions require the
eighth capture; abort branching cannot produce a completed receive write.

Both simulators also agree on 18 explicit reset/disable/isolated-loader aborts
and 18 fresh public reload/read recoveries without another chip reset. Current
generic whole-chip counts are 27,065 primitive cells / 4,278 state bits for
od128 and 51,723 / 8,343 for literal255, including every program-store bit.

The larger literal control passes all 1,160 cases in Icarus. Its first full
second-simulator launch rejected the redundant constant comparison before
simulation. After correction, the 32-case smoke and public boundary tests pass
both simulators. Its complete corrected two-simulator matrix remains a CI gate.

## Failures and remaining work

The expanded address space exposed a real legacy-skip overflow: word 254 plus
two wrapped to zero. The retained public counterexample fails; both immediate
and delayed overflow now fault without wrapping. E0035 also retains runner,
result-parser and lint failures instead of erasing unsuccessful attempts.

The arbitrary-word store induction timed out at 240 seconds for each capacity;
reachable covers passed. This is inconclusive, not a store proof. An alternative
comparison against an independent behavioral memory is a separate experiment.
Mapped area, routed timing, fanout, official precheck and real-netlist protocols
have not been measured for this candidate. Generic logic counts cannot close
those gates. No release or package should describe G2 as qualified yet.

Next: close the store proof and exact-commit CI gates, then measure the current
candidate under the unchanged pinned 8x4 CMOS5L flow. Retain any physical failure
and revisit capacity or general instructions using measured evidence. Promote
production and publish a qualified milestone only after the remaining G2 checks.

Specification: [general I/O candidates](../specs/g2-general-io-candidate.md).
Evidence: [E0035](../../evidence/E0035-general-i2c/README.md).
