# Learning labs

Each lab follows **explain → predict → run → inspect → restate → record**.
The prediction is important: it turns command execution into model building.

## Lab 0 — Is the repository internally consistent?

**Idea:** A static checker can compare names and configuration without running
the chip. It catches mismatched metadata, but cannot test Verilog behaviour.

**Predict:** The command should report a pass followed by a limitation.

**Run in the locked workbench:**

```powershell
.\tools\workbench.ps1 Check
```

**Inspect:** Read both output lines. Identify one fact it checked and one thing
it explicitly did not check.

**Restate:** “The repository metadata agrees internally, but this command did
not simulate or physically build the chip.”

## Lab 1 — Read one clock transition

**Idea:** The counter changes only on the rising edge of `clk`. Reset wins over
enable, and disabling the counter preserves its value.

**Predict:** Starting at `00`, with reset released and enable asserted, three
rising edges should produce `01`, `02`, `03`.

**Run:**

```powershell
.\tools\workbench.ps1 test
```

**Inspect:** Open the retained FST waveform and find `clk`, `rst_n`, `ena` and
`uo_out`. Check the prediction at the first three active edges.

**Restate:** Explain why changing an input halfway between rising edges cannot
immediately change the counter state.

## Lab 1A — Check the ingredient batch

**Idea:** A result is reproducible only when we can identify the tools that
produced it. `Doctor` compares installed version outputs and dependency hashes
with the machine-readable lock.

**Predict:** Every required tool should say `PASS`, followed by a limitation
that tool identity alone does not prove the RTL correct.

**Run:**

```powershell
.\tools\workbench.ps1 Doctor
```

**Inspect:** Find Icarus, Verible, Yosys, SBY, one solver and the Python lock
hash. Then open `tools/workbench/toolchain.lock.json` and match one value.

**Restate:** Explain why “I used Yosys” is weaker evidence than naming its exact
version, input commit and command.

## Lab 2 — Distinguish source logic from physical evidence

**Idea:** Yosys can translate the design into generic logic quickly. LibreLane
maps it to IHP cells, places those cells, routes wires and checks timing.

**Predict:** Generic synthesis can report an eight-bit register but cannot give
a trustworthy CMOS5L post-route timing margin.

**Run:** Compare:

```powershell
.\tools\workbench.ps1 synth
```

with the recorded official GDS workflow evidence.

**Inspect:** Find the generic cell statistics, the CMOS5L cell names, and the
post-route setup and hold slack. Note which tool produced each number.

**Restate:** Explain why “Yosys passed” and “the design meets 50 MHz after
routing” are different claims.

## Lab record template

For every later lab record:

1. Question
2. Prediction
3. Source revision
4. Command and tool identity
5. Observation
6. What this proves
7. What this does not prove
8. Next action
