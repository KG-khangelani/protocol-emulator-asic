# Learning labs

Each lab follows **explain → predict → run → inspect → restate → record**.
The prediction is important: it turns command execution into model building.

## Guided M0 tour — start here

Start with the smallest signal lesson. It uses only the Python standard library,
so the PowerShell wrapper runs it directly on Windows when Python is available;
Docker and the EDA tools are not needed:

```powershell
.\tools\workbench.ps1 LearnM0 RTL
```

It translates `clk`, `rst_n`, `ena`, and hexadecimal `00`, then works through
one hold row before asking for a prediction. Next ask the repository what is
technically complete and what still needs a human demonstration:

```powershell
.\tools\workbench.ps1 LearnStatus
```

This command will never convert green CI into a human fluency pass. It shows the
current criteria and the next small teach-back. If the individual tools are
still unfamiliar, continue with the complete read-only tour:

```powershell
.\tools\workbench.ps1 LearnM0
```

It reads the exact archived M0 RTL, E0007 fast-verification record, E0010
physical record, JUnit results, and tool lock. It then connects each plain-
language claim to its concrete number or source line. To revisit only the
generic-synthesis-versus-physical-fit distinction, run:

```powershell
.\tools\workbench.ps1 LearnM0 Physical
```

`LearnStatus` and `LearnM0` prefer host Python and fall back to the locked
container only when host Python is unavailable. They validate that their inputs
agree, but they cannot validate human understanding. The final restatement
remains a conversation and is never auto-marked as a pass.

`Evidence` also reruns the waveform lab and retains its VCD and JUnit result, so
the teaching command is checked in CI. That still validates software behaviour,
not the learner's explanation.

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

**Run the readable waveform lab:**

```powershell
.\tools\workbench.ps1 LearnWaveform
```

**Inspect:** Read the printed reset, count, wrap, hold, resume and reset-priority
rows. The underlying text waveform remains at `build/m0-learning.vcd`; a full
viewer can display it later, but no viewer knowledge is needed for this lab.

**Restate:** Choose one printed row. Name the sampled `rst_n` and `ena` values,
say whether `uo_out` changed, and explain why. Then explain why changing an
input halfway between rising edges cannot immediately change the counter state.

## Lab 2 — Ask a second simulator

**Idea:** Icarus and Verilator are independent implementations. Agreement makes
a simulator-specific mistake less likely, while both still share the same test
oracle and can therefore share the same blind spot.

**Predict:** Both commands should report the same two passing cases and the same
simulated end time of 31,220 ns.

**Run:**

```powershell
.\tools\workbench.ps1 Test
.\tools\workbench.ps1 TestVerilator
```

**Inspect:** Compare `test/results.xml` with `test/results-verilator.xml`. Note
that Verilator first translates the hardware into C++ and invokes `g++`.

**Restate:** Explain why two agreeing simulators increase confidence without
turning the finite test scenarios into a proof of every input sequence.

## Lab 3 — Check the ingredient batch

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

## Lab 4 — Try every allowed digital control sequence

**Idea:** Simulation samples chosen scenarios. Formal verification translates
the RTL and its assertions into equations, then asks a solver whether any
allowed state or input sequence can break a rule.

**Predict:** The real M0 design should prove reset/count/hold/output properties,
the cover task should reach `FF` and then `00`, and the intentionally wrong
increment-by-two design should produce a counterexample rather than pass.

**Run:**

```powershell
.\tools\workbench.ps1 Formal
```

**Inspect:** Find `DONE (PASS)` for `prove` and `cover`. Then find the mutant's
expected assertion failure at step 2 and its counterexample trace under
`build/formal/mutant/`. Open `formal/m0_gpio_formal.sv` and map one assertion
back to a row of the M0 state-transition table.

**Restate:** Explain why the real proof plus a rejected mutant is stronger than
either result alone, and why neither establishes physical timing or analog
behavior.

## Lab 5 — Distinguish source logic from physical evidence

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
