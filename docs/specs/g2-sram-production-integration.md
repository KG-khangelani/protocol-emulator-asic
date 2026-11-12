# SRAM continuation of the G2 production integration gates

Keep the [six original integration gates](g2-production-integration.md).
The candidate remains the exact E0042 five-file source manifest, interface 0x22,
128 logical words and unchanged instruction timing. Production adoption waits
for the complete official physical artifact audit.

Declare `od128-sram` as an additional exact source profile. Normal verification
commands must evaluate the selected source directory and the exact two vendor
digital models. Reject unknown source or model bytes. Keep the historical
eight-word profile and D39 profile separate, including their original evidence.

Require both complete 30-group simulator suites and all prior reference records,
the bank control, source-bound engine equivalence/reset proof, actual SRAM
arbitrary-word induction and its four coverage witnesses/checked stale-lane
counterexample, all four real store mutations in both simulators, current
instruction proofs/controls, data-store/synchronizer/public-readout assertions
and the host deadline check. Keep the complete ten-task historical formal
baseline on its archived sources. The previous whole-chip proof timeouts remain
incomplete; do not substitute their labels for these compositional results.

Add a bounded proof for the new prefetch output itself: after one observed
clock, the actual registered program counter equals the previous prefetch
output, under arbitrary instruction, reset and enable inputs. Initialize only
the proof observer's valid flag, with no assumptions or design-state reset.
Require an independently reached moving-PC cover and a real counterexample
after flipping one prefetch output bit. Bound each task to 120 seconds. This
checks address prediction; SRAM data/reset behavior remains a separate proof.

Preserve the identified RTL during physical qualification. An initial Verible
screen finds exactly two `always-comb` style warnings, one on the generated
engine's next-state block and one on the SRAM store's combinational read mux.
Both use standard Verilog `always @*`. If scoped style handling is needed,
require those exact source bytes, two exact warning locations/categories and
all remaining style rules to pass. No latch, timing or functional check is waived.

Generic synthesis must retain one real macro as a black box and report its
8192 physical bits separately from standard-cell state. It cannot claim IHP
area or timing. The smoke waveform is an RTL harness check; it must never be
labelled a physical netlist test. Reusable receipts bind the actual source,
models, proof/test code, runtime and all retained files; repository metadata
checks run fresh when collecting evidence.
