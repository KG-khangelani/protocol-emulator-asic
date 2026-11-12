# G2 bounded banked-read screen

Predeclared 2026-11-12 after all three 128-word physical trials failed global
routing. D39 reduced mapped area by 15.3974% from original od128 but did not
route. This screen changes only its combinational program-store read network.

Hypothesis: sixteen eight-word selectors followed by one bank selector may
reduce read-network cost or provide a more useful placement structure. This
is a hypothesis; neither RTL hierarchy nor generic cell savings establishes
physical locality or a routed saving. The synthesis tool may erase the change.

Start from the five exact D39/E0038 files. Keep the complete clocked store
block byte-identical, including all 4,096 data bits, reset, enable, writes,
bank/length/ready transitions. Keep the other four modules byte-identical.
The loader/PC address choice, byte readback, length override and fetch-valid
expression stay unchanged. Select the low three address bits within sixteen
groups, then select the group with bits [7:3]. Include explicit defaults so
out-of-range and unknown selections retain the existing zero behavior.
Add no state, clock, latency, capacity, interface or instruction change.

Bound the screen to this one candidate, one matched generic synthesis per
parent/candidate (300 seconds each), complete-store temporal equivalence
(240 seconds) and an independently initialized reset base (90 seconds).
Check the actual models: all 4,109 store state bits and every output bit must
be compared; no abstract storage, assumed environment or excluded state.
Temporal proof uses corresponding state; the separate reset proof establishes
that correspondence after one sampled synchronous reset. Compare raw outputs
in every mode, without D39's earlier conditional-output masking.

Run a deterministic port-driven store test in both simulators: populate/read
all 512 bytes, fetch all 256 PC values, check bank/length/enable/reset and
unknown selector behavior where the simulator supports four states. The same
test must reject a high-bank alias mutation after real reset and byte writes.
Retain exact source, tool identity, scripts, logs, models and counterexample.
A compile error or timeout is not a successful negative control.

Advance only if the proofs and controls pass and measured generic cost or
structural evidence merits a fresh physical trial. Otherwise retain the result
and revise direction. Before any production adoption, require a new decision,
the full G2 regression/formal matrix and pinned 8x4 CMOS5L routing, timing,
precheck and actual-netlist public tests. All physical limits remain unchanged.
