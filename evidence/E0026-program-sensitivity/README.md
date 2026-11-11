# E0026 - Actual-program sensitivity

Observed 2026-11-11 in the locked Docker workbench, baseline main213e391.
**Written-program sensitivity is qualified locally.** Terminal formal covers
remain inconclusive. Production and candidate RTL are unchanged.

The [frozen plan](../../docs/specs/spi-program-sensitivity.md) separates
proof sensitivity, actual bad-firmware behavior and reachability.

| Check | Result |
|---|---|
| Unchanged E0025 conjunction | Inductive PASS, depth12/180s, 32.881s |
| Invert public MOSI goal only at first drive | Required reachable FAIL, 18.769s; trace cycle39 shows actual MOSI obeying TX while the changed goal demands the opposite |
| Remove only first sampled-MISO premise | Required reachable FAIL, 32.437s; trace cycle65 has target RX0x01/LSB-first and sampled MISO0 |
| Icarus public controls | Six transactions PASS: two baseline and four correctly rejected controls |
| Verilator public controls | Same six PASS; complete records byte-identical to Icarus |
| Concrete LSB terminal cover | INCONCLUSIVE:180.088s timeout, no witness |
| Concrete MSB terminal cover | INCONCLUSIVE: interrupted at last logged check379, no final status/witness |

The formal negatives use BMC42 and BMC72. They fail at the public GPIO and
synchronized-input assertions with checked witnesses. UNKNOWN or an
induction-only failure would not satisfy these controls.

[model-audit.json](model-audit.json) confirms all five generated models retain
412 actual DUT bits plus55 harness/history bits and82 assertions. Eight
assumption cells remain syntactically present; the missing-premise case
disables only the first condition. The baseline's eight compiled source/include
texts equal E0025. There is no abstract fetch, forced state or substitute memory.

## Actual firmware counterexample

Finite controls use uninstrumented compact RTL, actual public loading/readback,
and the independent pin/time oracle. Both orders use TX0x96/target RX0x69.

| Image/input | Wire RX | Raw result LSB/MSB | HALT | Accepted |
|---|---|---|---|---|
| Normal, response499999ps | 0x69 | 0x69 / 0x69 | 0xa7 | Yes |
| Early SAMPLE, same lawful input | 0x69 | 0xd3 / 0xb4 | 0xa7 | No |
| Normal, response500001ps outside aperture | 0xd3 / 0xb4 | 0xd3 / 0xb4 | 0xa7 | No |

Early SAMPLE compensates its delay with WAIT, preserving external SCK/CS/MOSI.
The image check compares against the actual supplied mutant bytes. Its failure
therefore measures external data behavior, not stale image expectations.
HALT and valid alone cannot qualify a transfer. JUnit/logs, canonical records
and compressed complete public traces are under [simulation/](simulation/).

## Preserved failures and interruption

First Icarus could not import a generated module. A source module outside the
test directory plus explicit PYTHONPATH still failed on Icarus; Verilator
passed both attempts. The final fix uses the normal
test/test_spi_program_controls.py entry point. Both simulators then pass.

During the second failed attempt the module moved before its aggregate
finished, and its source-drift check failed. That failed run is retained.
The final simulation attempt starts/ends with matching hashes. Formal jobs
were not rerun for these simulation-only repairs: the AST audit verifies all
four formal execution/witness-check functions stayed unchanged. Original
runner snapshots and results remain under [failures/](failures/).

The first cover exhausted its fixed budget. The second stopped without a
result; no experiment container remained at recovery. The original aggregate
still says RUNNING and is preserved in
[interrupted-cover-run-result.json](interrupted-cover-run-result.json).
[result.json](result.json) adds the recovered interpretation. No cause of
interruption, second timeout, cover PASS or formal reachability is inferred.
No budget increase or alternate cover configuration was attempted.

## Reproduction and limits

Run inside the locked workbench:

    python3 experiments/spi_phase/run_program_sensitivity.py --output build/spi-program-sensitivity/new

The default requires the inductive baseline, both checked counterexamples,
six public cases per simulator and identical records. The separate CI workflow
runs this gate. --simulation-only labels finite evidence explicitly;
--reachability-only selects the separate bounded covers.

Curated hashes, commands, inputs, logs and deterministic gzip witnesses are
retained. Original trace hashes are in the formal run manifest. Large generated
models remain ignored. This establishes sensitivity of written properties,
not completeness, arbitrary firmware, physical timing/fit, four-mode SPI,
Fmax or owner fluency.

[D27](../../docs/decisions/0027-program-sensitivity-and-next-protocol-contract.md)
moves the next slice to an explicit four-mode pin/timing contract. Deep terminal
covers require a new method before another attempt; their results remain
inconclusive and do not erase the finite completion witnesses.

Curation normalizes log line endings/trailing whitespace and JSON-escapes exact
patch text. result.json records original hashes and each transformation; failed
outcomes are unchanged. Original patch bytes are recoverable from original_text.

## Remote qualification

The complete default gate passes on clean implementation commit0eaa54c in
[run43102775075](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43102775075),
including artifact upload. [remote-qualification.json](remote-qualification.json)
records the artifact identity and verified ZIP digest;
[remote-run-result.json](remote-run-result.json) retains all outcomes.
Every recorded input hash matches the exact Git blob at that commit.
This reproduces the full default gate after the local import fix; it does
not rerun or promote either inconclusive cover.
