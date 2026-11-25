# E0067 — Can the stock probes resolve the SPI handoff?

The Siglent SDS2204X Plus listed by Communica can acquire all four analog channels at up to 1 GSa/s per channel, a 1 ns sample interval. Its standard kit includes four PP215 passive probes. On the council's reference circuit, the capacitance of those probes alone can keep the measured branch current above the release threshold for tens of nanoseconds after an instantaneous turnoff. The next equipment quote should include a demonstration of the loaded fixture with known release times and both bias polarities. [Local scope listing](https://www.communica.co.za/products/sds2204x-plus) · [Acquisition modes, pp. 7–8](https://www.siglenteu.com/wp-content/uploads/dlm_uploads/2024/07/SDS2000X-Plus_Datasheet_EN01D.pdf) · [Manufacturer's standard probe list](https://siglentna.com/wp-content/uploads/dlm_uploads/2026/06/Oscilloscopes-standard-probes-and-other-accessories-20260320.pdf)

## What the probe adds

Siglent's EN02C probe data sheet specifies 13–17 pF at 10× for the PP215. An earlier Siglent data sheet gives 16–20 pF for the same part number. Confirm the supplied revision and measure the response with the actual probe tips, short grounds, receiver and wiring attached. An instrument calibration certificate can identify the scope and its calibration. The complete fixture also needs a differential-voltage and channel-timing check. [EN02C probe data, passive probe table](https://siglentna.com/wp-content/uploads/dlm_uploads/2026/06/Probe_DataSheet_EN02C.pdf) · [Earlier V1.5 probe data, p. 1](https://siglentna.com/wp-content/uploads/2018/01/SIGLENT-Probe-Datasheet-V1.5.pdf) · [Scope accessories and certificate](https://www.siglenteu.com/wp-content/uploads/dlm_uploads/2024/07/SDS2000X-Plus_Datasheet_EN01D.pdf#page=17)

The calculation uses the E0049 Arty reference circuit at 3.3 V with 200 Ω in the driven path, a 470 Ω sense resistor and a 1 kΩ opposing bias. The two nodes start in the settled, opposed-drive state. At time zero the driver opens instantaneously. Each node then discharges or charges through the passive network. The first four rows set the *entire* capacitance of each node equal to one probe tip. The fifth adds an illustrative 10 pF per node to a 17 pF tip. A different driver impedance, unmatched capacitances or the wiring on the Lattice breakout will give different values. [Original circuit, equations and thresholds](../E0049-review-council/panel-b/fixture/bench.md) · [Lattice measurement points](../E0063-local-breakout/README.md#assemble-the-proposed-fixture)

| Capacitance per node | Time to 0.25 mA | Time to 0.162394 mA | Current magnitude at 8 ns | Current magnitude at 56 ns |
| ---: | ---: | ---: | ---: | ---: |
| 13 pF | 46.474 ns | 59.162 ns | 0.964 mA | 0.181 mA |
| 16 pF | 57.199 ns | 72.815 ns | 1.042 mA | 0.258 mA |
| 17 pF | 60.774 ns | 77.366 ns | 1.065 mA | 0.283 mA |
| 20 pF | 71.499 ns | 91.019 ns | 1.128 mA | 0.352 mA |
| 27 pF | 96.523 ns | 122.875 ns | 1.248 mA | 0.485 mA |

The council's proposed strong-drive release band is 0.25 mA including uncertainty. If the full 40 mV differential error allowance and a 1% resistor tolerance apply, the largest nominal reading that satisfies this band is 0.162394 mA. This solves `I + (40 mV + I × 4.7 Ω) / 465.3 Ω ≤ 0.25 mA` for current magnitude `I` in mA. A more precise measured resistor or a smaller differential error changes that limit. Values in the table exclude timing uncertainty. The model checks symmetry for the two opposing drive/bias directions and compares both node voltages with the council's independent fourth-order numerical integrator to within 10 nV over 160 ns. These checks establish numerical consistency of the circuit model.

## What to request at the bench

The earlier FabricFox SPI sweep gave at least 56 ns from digital disable to reselection at a requested 480 ns gap, and only 8 ns at 424 ns. The model shows how an immediately released reference can still carry enough discharge current to miss either margin at a single sample. The margins belong to the remote FPGA. Measure the actual select and enable intervals again on the Lattice board. [Digital sweep](../E0057-remote-spi/README.md#how-much-time-the-requester-left-between-selections) · [Opposing-bias observations](../E0065-spi-branch-bias/README.md)

1. Use the actual probes and load to capture known driven-high, driven-low and released controls under both bias directions. Deskew using a common edge and measure differential zero at matched DC levels. Retain the control traces and the actual sense resistance.
2. Capture a known immediate release and deliberately delayed releases bracketing the observed clearance. Start with the 480 ns requester schedule. Include the measured decay of the reference, repeatability and crossing slope in the time bound. The council's proposed total limits are 40 mV differential and 5 ns timing uncertainty.
3. If the known early and late controls overlap after uncertainty, record the interval as unresolved. Try a lower-capacitance probe pair or a characterized differential probe, then repeat the same controls. A positive receiver turnoff result requires separable reference states and a bounded target measurement in both polarities. [Bench acceptance criteria](../E0049-review-council/panel-b/fixture/bench.md)

On 26 November 2026 SAST both public FabricFox endpoints reported an FPGA present and reachable. Their published wiring provides GPIO observations. A fresh Windows device check found COM1 and six Bluetooth serial ports. Physical measurements still require an accessible calibrated target-branch instrument or, for the sensor trial, access to the two real DS18B20s and their power connections. [Board 1 status](https://tinytapeout.fpgas.online/board/fpga-1/status.json) · [Board 4 status](https://tinytapeout.fpgas.online/board/fpga-4/status.json) · [Provider pin map](https://docs.fpgas.online/en/latest/boards/tt-fpga/overview/pin-mapping.html) · [Western Cape counters](../../docs/research/western-cape-bench.md)

Reproduce the table from the repository root with standard Python. The script reuses the retained council model. It produced identical numbers on Windows and in the locked Linux workbench.

```powershell
python -B evidence/E0067-probe-loading/estimate.py
```
