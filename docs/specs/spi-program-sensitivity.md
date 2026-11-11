# Actual-program proof sensitivity and reachable witnesses

Status: frozen experiment plan, 2026-11-11. Baseline `213e391` includes the
completed PR8 integration. This closes a verification gap after E0025 and
changes neither production nor experimental candidate RTL.

E0025 proves its written conjunction under a fixed public loading/execution
sequence and eight sampled-MISO premises. Test whether that conjunction
detects observable mistakes, and seek explicit terminal witnesses. Preserve
all earlier failures/timeouts. No physical, four-mode, arbitrary-firmware or
owner-fluency promotion follows.

## Formal controls fixed before execution

Reuse E0025's actual compact top, stores, synchronizer, reversible read-only
taps and asserted invariants. Keep original public inputs symbolic.

| Case | Single change | Configuration | Required result |
|---|---|---|---|
| Baseline | None | prove, depth12, Z3, 180s | Actual inductive PASS |
| Wrong public MOSI goal | Invert expected MOSI only at completed execution edge2 | BMC, depth42, Z3, 180s | Reachable FAIL at the public GPIO goal, with a counterexample |
| Missing first input premise | Drop only the j=0 rising-edge MISO assumption | BMC, depth72, Z3, 180s | Reachable FAIL showing the wrong first sampled bit or partial receive state |

Run each configuration once. Timeout, missing status, tool error and induction
failure without a reachable counterexample do not satisfy a negative control.
Retain exact inputs, commands, status, logs and witnesses. Terminate the whole
solver process group on deadline. No increased budget or adaptive proof retry.

## Public firmware and input controls

On each of Icarus and Verilator run six public-pin transactions: TX=0x96,
target RX=0x69, both orders, with baseline, early-SAMPLE firmware, and a late
input profile. Reuse the independent pin/time oracle and actual loader/readback.
The image check must compare against the image actually supplied.

For baseline and early-SAMPLE use response499999ps after each falling edge,
one picosecond before the rising sample. The early image compensates its
one-edge-early SAMPLE with an extra WAIT edge. Require correct SCK/CS/MOSI and
wire RX=0x69, but raw RX=0xd3 LSB-first or0xb4 MSB-first. HALT/valid alone must
not accept it. The late-input control uses response500001ps on every bit;
retain the actual wire/raw bytes and reject the violated envelope.
These are finite public observations, not proofs of arbitrary firmware.

## Separate terminal reachability attempts

Run two cover jobs: TX=0x96/RX=0x69, one per order, depth444, Z3, 180s each,
once. Narrow only public inputs to the lawful deterministic E0025 preflight:
select_valid follows cycle parity; MISO holds each intended bit from its
rising-edge tick. Add one cover at cycle440 for public HALT status0xa7 and
actual RX=0x69/valid. No internal force, preload or new assumption.

Cover mode does not check the retained assertions; baseline induction and
finite simulations remain separate. Disclose simplification due to concrete
inputs. These covers establish two reachable examples, not universal behavior.
If a cover times out, retain INCONCLUSIVE and simulation witnesses separately.
The cover experiment is optional in the runner and is not silently made a
required passing CI gate before its outcome is measured.
