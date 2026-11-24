# SPI handover counterexample and 3.3 V measurement fixture

The [formal rebuttal](formal-rebuttal.md) gives the ranking and competing argument. The [bench protocol](bench.md) specifies two-sided voltage/current measurements, calibration, component identities, numerical acceptance and conditional effort. The [predeclared contracts](fixture-contract.md) distinguish the circuit calculation from the digital experiment.

- All four normal A5 frames return A7. The one-way branch drives all eight command bits. The ideal bilateral branch disconnects during CS high then reconnects the stale first response if CS falls at 160 ns. A complete new A4 frame receives no 3C after a stopped first response. The inhibited switch remains electrically isolated while the second service request goes unanswered. The raw observed-state table is included for both peer values and all four switch modes. Each of 20 cases is byte-for-byte equivalent after decoding into fields on RTL and the original G4-gate functional model. [Result](results/switch-reselect.json)
- Instantaneous turnoff on a nominal 3.3 V, 200/470/1,000 Ω two-node fixture crosses the 0.25 mA discrimination threshold at 42.899 ns for 12/12 pF and 214.496 ns for 60/60 pF. This distinguishes detector loading from actual MISO driving. [Result](results/fixture-sensitivity.json)

## Reproduction

The exact 498-step loader plan has SHA-256 `16f016a699ee92431bede9995e396d23af35e4f5f83998bf64a22438b47811a9` and loads the 59-word image with SHA-256 `8d257ace7cc236c3ff5b2b71242679422f81900b6ee10dbd0daa78a7f318a81e`. It came from panel C's released-assembler program. The source verifies the G4 archive, RTL/SRAM and standard-cell functional models before execution. [Program and independent C qualification](../../panel-c/spi-target/README.md) · [Earlier powered-netlist I²C matrix](../../powered-netlist/i2c-matrix/result.json) · [Passed G5/G3 cross-representation screening](../../powered-netlist/cross-release-contract.md)

From this directory, in PowerShell 7 with the existing locked workbench image and pinned PDK Docker volume, pass a fresh output directory on H:. The driver mounts the checkout, records and PDK read-only, compiles large intermediates into anonymous process memory, publishes the two JSONs and compares every field to the retained results.

```powershell
.\replay.ps1 -ScratchRoot H:\temp\protocol-council-fixture-replay
```

Optional `-PdkVolume NAME` selects an existing volume with `ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008`. The fixture calculation also runs with standard-library Python using `python -B fixture_sensitivity.py`. The documented first generation and a fresh-directory rerun used the unchanged project workbench. The electronics cited in the bench plan are prospective equipment.
