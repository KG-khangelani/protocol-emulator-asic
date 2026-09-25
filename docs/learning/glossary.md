# Project glossary

Definitions here are deliberately tied to this repository. Extend this file
when a new term first becomes necessary.

| Term | Plain-language meaning | Where to see it here |
|---|---|---|
| ASIC | A chip built for a particular purpose rather than a general desktop processor. | The final output targeted by the project. |
| Clock edge | The instant when synchronous state is allowed to change. | `always @(posedge clk)` in `src/project.v`. |
| RTL | Source code that describes registers and the logic between them. | `src/project.v`. |
| Test oracle | An independent rule for what the design should output. | The Python-side expected counter in `test/test.py`. |
| Simulator diversity | Running the same oracle through independently implemented simulators to expose tool-specific behavior. | Icarus `results.xml` and Verilator `results-verilator.xml`. |
| Waveform | A time plot of digital signal values. | `test/tb.fst` after simulation. |
| FST | A compact binary waveform format suited to saving complete regressions. | Normal `Test` output at `test/tb.fst`. |
| VCD | A readable text waveform format; larger than FST but convenient for teaching and simple tools. | `build/m0-learning.vcd` after `LearnWaveform`. |
| Formal verification | Exhaustively searches the mathematical model for a counterexample to stated properties. | `formal/m0_gpio_formal.sv` and `build/formal/`. |
| Assertion | A rule the implementation must satisfy for every allowed formal state. | Reset/count/hold/output rules in the M0 formal harness. |
| Assumption | A restriction on the environment; an incorrect one can hide real failures. | Used only in the M0 cover task to request a readable wrap witness. |
| Cover property | A request for one reachable trace demonstrating a state or event. | M0 traces reaching `FF` and wrapping to `00`. |
| Counterexample | A solver-generated input/state trace that violates an assertion. | The expected failure trace for the increment-by-two mutant. |
| Synthesis | Converts RTL into a network of logic cells. | Generic Yosys output and the CMOS5L synthesis report. |
| Standard cell | A pre-designed logic building block supplied by the process library. | `sg13cmos5l_*` cells in the physical synthesis report. |
| PDK | The process design kit: manufacturing rules, cell data and tool files for a fabrication process. | IHP `ihp-sg13cmos5l`. |
| Place and route | Chooses physical cell locations and wires their connections. | LibreLane reports under the official `gds` workflow. |
| Timing analysis | Calculates whether paths meet their required arrival times over process corners. | Post-route setup and hold reports. |
| Setup slack | Time remaining before data would arrive too late. Positive is comfortable; negative is a violation. | Post-route timing metrics. |
| Hold slack | Time margin against data changing too soon after a clock edge. Positive is comfortable; negative is a violation. | Post-route timing metrics. |
| DRC | Design-rule checking: tests layout geometry against encoded manufacturing rules. | Tiny Tapeout precheck and physical reports. |
| LVS | Layout-versus-schematic: compares layout connectivity with the intended netlist. | LibreLane physical reports. |
| Gate-level netlist | Verilog containing mapped cells and connections rather than the original behavioural RTL. | Produced by the GDS workflow for `gl_test`. |
| GDS | The binary geometry database delivered by the layout flow. | `tt_submission` artifact from the GDS workflow. |
| Reproducibility | Ability to identify and rerun the same source, tools and configuration. | Evidence manifests and `tools/workbench/toolchain.lock.json`. |
| SHA-256 | A content fingerprint used to detect a changed artifact. | Artifact hashes in `evidence/`. |
| `PASS` | The stage ran and met its stated acceptance condition. | Evidence stage status. |
| `FAIL` | The stage ran and contradicted its acceptance condition. | Evidence stage status. |
| `BLOCKED` | The stage could not run because a prerequisite was unavailable. | Evidence stage status. |
| `NOT_EVALUATED` | No adequate test was performed, so no conclusion is permitted. | Evidence and research claims. |
