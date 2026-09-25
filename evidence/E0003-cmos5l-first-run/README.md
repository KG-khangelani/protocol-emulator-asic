# E0003 — First official CMOS5L physical run

GitHub run [35990661423](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/35990661423)
tested commit `0248b2f682f9cc31025f9b36d0cee27235ffafbb` on 24 September 2026.
The GDS job passed and every Tiny Tapeout precheck passed. The gate-level job
failed during compilation, so the workflow's correct overall result is
**FAIL**, not a completed M0 result.

## What the passing physical stages establish

The flow converted the M0 RTL into a placed-and-routed CMOS5L layout inside the
6x4 allocation. It reported 58 mapped synthesis cells (803.7792 µm²), 80 final
standard cells (1,166.66 µm²), and 0.129282% standard-cell utilization. The
worst setup slack was +13.585833 ns and worst hold slack was +0.172078 ns across
the recorded corners at the 20 ns target. Route DRC, Magic DRC, LVS, antenna,
setup, hold, slew, fanout and capacitance violation counts were all zero.

All nine prechecks passed, including the SG13CMOS5L KLayout DRC, pin, boundary,
layer and cell-name checks. The final 4,189,814-byte GDS has SHA-256
`8195be3450979ec0f279c7529d5165b13d4bde143a07b2789051ed39027dcd71`.
Selected raw values are preserved in `selected-metrics.csv`; artifact and tool
identities are in `result.json`.

In plain language: the tools found a physically routable arrangement with
timing margin at the requested 50 MHz target. This does **not** prove a maximum
frequency, fabricated-silicon behavior, or protocol capability.

## Why the gate-level stage failed

Gate-level simulation asks whether the post-synthesis cells still implement the
specified pin behavior. Icarus stopped before running a test because the PDK
standard-cell model instantiates the primitive `ihp_dff_r` eight times, while
the project's gate-level source list omitted `sg13cmos5l_udp.v`, the file that
defines that primitive. No JUnit result or waveform was produced.

The next falsification step is deliberately narrow: add the UDP model before
the standard-cell model, run the exact archived netlist in a container, and
then rerun the official workflow. Until that passes and a clean rerun is
recorded, M0 remains in progress.

## Known limitations retained from the logs

- PNR and signoff used LibreLane's generic fallback SDC.
- The flow emitted OpenROAD thread and unsupported LEF58 enclosure warnings.
- No long-wire threshold was configured.
- IR-drop analysis had no explicit voltage-source-location file.
- KLayout DRC was disabled inside LibreLane; the separate Tiny Tapeout
  precheck did run and pass its KLayout checks.
- Large downloaded artifacts remain under ignored `build/artifacts/E0003/`;
  GitHub retains the originals until 23 December 2026.
