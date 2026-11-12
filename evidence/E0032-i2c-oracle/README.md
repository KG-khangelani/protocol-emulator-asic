# E0032 - Independent I2C contract and public-event oracle

Date: 2026-11-12. Decision: [D36](../../docs/decisions/0036-i2c-contract-before-isa.md).
Scope: **reference fixtures and acceptance code only; no DUT execution**.

The frozen [contract](../../docs/specs/p-i2c-controller-100k.md) covers one-byte
write/read and combined repeated-START transactions on ordinary seven-bit
addresses. Public output values, directions, resolved wires, raw result/valid
and execution state determine acceptance. The oracle imports no ISA, executor,
compiler, program generator or fixture module.

## Reproduce

Inside the locked workbench, from the repository root:

```sh
make doctor
make check
python3 experiments/i2c/qualify_oracle.py --output build/i2c-oracle
```

`qualification.json` records the source identities, fixed seed 19669030
(0x12c2026), scope and result counts. `cases.jsonl` contains all 3,902 observed
inputs, trace hashes and error kinds. Its witness links point to 53 complete
input/report files. `SHA256SUMS` covers curated artifacts. The reproduction
directory and parent-revision metadata may differ; compare source identities,
case records and witness contents. Unit log elapsed time is not deterministic.

## Observed result

All 19 groups pass: 3,650 OK observations, six NACK, 152 timeouts, 18 explicitly
declared aborts and 76 rejected observations. Counts include repeated judgments
of a fixture and malformed inputs; they are not counts of unique chip transfers.

The principal positive matrix covers 3,072 byte/kind/target-phase fixtures,
336 ordinary-address fixtures, six NACK boundaries, 77 single/all-release
stretch fixtures, and 304 deadline-neighbour/permanent-low fixtures. Additional
hand-calculated and threshold cases exercise exact timing and result lifetime.
Time is sampled on a 5 ns grid with 20 ns core edges. Nominal clock rate is
100 kHz; the oracle measures actual periods and rejects faster transfers.

The controls reject wrong bits/address/order, missing/extra clocks, wrong ACK,
continued data after NACK, bad repeated START, active-high drive, high-phase
ownership changes, target-generated clocks, short intervals, late valid data,
advance during stretch, early/late timeout, failed release and stale RX.
Reset/disable/loader fixtures verify explicit abort effects at six different
cuts. A truncated normal trace is rejected.

`development.json` retains a false-pass experiment: deleting clock ownership
and release-count guards allows the target to supply the clocks while the
resolved wires remain correct. The final checker rejects the same trace. An
initial test-edit NameError is also recorded; the repaired full suite passes.

## What this does not establish

No ISA extension or RTL execution has occurred. Actual public loading,
initialization, target isolation, synchronizer flush, both simulators, relevant
formal assertions and fresh physical evidence remain G2 gates. The event
adapter must record every transition; the oracle cannot recover omitted events.
Identical old/new bytes require internal capture provenance checks in addition
to public readout. Ideal digital fixtures establish no analog/electrical or
metastability result. G1 and owner-fluency evidence are unchanged.
