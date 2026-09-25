# E0007 — Locked fast CI and M0 formal proof

GitHub run [36119276357](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36119276357)
tested commit `c662a906a0328e2130ba6e70a26180200f1b1eaf` on 25 September
2026. Every fast verification stage passed inside the repository's locked
Linux/amd64 workbench. The workflow's recorded result is **PASS**.

## What passed

| Gate | Plain-language question | Result |
|---|---|---|
| Static checks | Are the project metadata, source list, clocks and Python files structurally consistent? | PASS |
| Verible lint | Does the RTL avoid the configured language and style hazards? | PASS |
| Icarus simulation | Does one simulator observe the two specified M0 behaviors? | 2/2 PASS |
| Verilator simulation | Does an independent simulator observe the same two behaviors? | 2/2 PASS |
| Formal safety proof | Do the written reset/count/wrap/hold/output/input-independence assertions hold for all modeled traces? | PASS by k-induction |
| Formal reachability | Can the constrained witness reach `FF` and then wrap to `00`? | PASS at steps 257 and 258 |
| Mutation check | Do the assertions reject an intentionally broken `+2` counter? | Expected FAIL detected at step 2 |
| Generic synthesis | Can Yosys lower the RTL to a 22-cell generic netlist? | PASS |

Both simulators ran `reset_wrap_hold_and_resume` and
`seeded_control_and_input_noise`, totaling 31,220 simulated ns per simulator.
The formal safety task used Z3 through SymbiYosys and completed both the
base-case and induction checks. Its safety proof makes no environmental input
assumptions. The cover-only task assumes a reset followed by continuous enable
so that it can produce a readable full-count witness; those assumptions are
not part of the safety claim.

The mutation result is intentionally red inside an overall green check. The
mutant changes the counter increment from `+1` to `+2`; the assertions catch
that defect at step 2. This is a small falsification test showing that the
property suite can reject at least one plausible implementation error.

## How to read this evidence

Simulation checks selected journeys through the design. Formal proof asks a
solver to cover every behavior allowed by the model for the properties we
wrote. Generic synthesis checks that the RTL can become gates, but it does not
place those gates on the IHP chip. These methods overlap, but none substitutes
for the others.

`manifest.json` records the clean source commit, source hashes, exact tool
versions, commands, and seven passing stages. The two JUnit files, three formal
logs, and generic `synth.json` are retained here so the detailed observations
remain inspectable after GitHub's artifact expires. Their hashes and the
original artifact identity are recorded in `result.json`.

## Remaining boundary

This evidence proves only the written M0 properties against the modeled RTL.
It cannot prove that the property set is complete, that fabricated silicon will
work, that 50 MHz is the maximum frequency, or that a protocol VM exists. The
separate pinned CMOS5L run must still close placement, routing, timing,
gate-level, and precheck acceptance.

The complete downloaded artifact remains under ignored
`build/artifacts/E0007-fast-ci-36119276357/`. GitHub retains the original
artifact until 24 December 2026.
