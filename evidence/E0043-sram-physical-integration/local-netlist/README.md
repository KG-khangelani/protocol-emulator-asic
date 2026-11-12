# E0043 - Both simulators pass the same routed netlist

Icarus and Verilator pass all eighteen public test groups on the identical
trial 03 routed netlist, SHA256
`4bd1cae07d6ba5344c784fe27f87b86d97696229a7b29fa8bdd16e1d7a0f1b06`.
Each reproduces all 1,052 SPI records, 1,160 I2C records, four boundary records
and 36 abort/reload records exactly. The runs take 3,661.519 and 6,096.736 seconds,
respectively, within their original 10,800-second bounds. The five RTL source
identities and both unmodified SRAM digital models match E0042.

This is zero-delay functional evidence. Trial 03's physical layout is rejected
for seventeen public-pin/power overlaps and deliberately stopped. Its explicit
stop record and geometry diagnosis are retained. These functional passes do
not qualify that layout or the different netlist from corrected trial 05.
The actual officially submitted corrected netlist still needs its own tests.

The initial Verilator compile rejects 84 `SPECIFYIGN` and 28 `PINMISSING`
warnings. The latter identify only unconnected outputs of intentional clock
load cells. A narrowly declared two-warning exception permits compilation,
but all eighteen tests then fail because the library's delayed reset alias
stays low. The earlier claim that these ignored timing constructs have no
functional role in the model was incorrect.

A separate cell probe compares 1,025 observations. Unmodified Icarus has zero
mismatches; unmodified Verilator has 249. An explicit simulation-only bind
connects `RESET_B` to `delayed_RESET_B` for the actual 353 `dfrbpq_1` cells.
Its observations exactly match Icarus. A deliberately stuck reset adapter
reproduces 249 mismatches. With the validated adapter, the unchanged full
netlist passes all eighteen groups in Verilator. The vendor libraries and
netlist are unmodified; neither four-state equivalence nor timing is claimed.

The 1,145-file archive retains both complete runs, original compile and
functional failures, two preflight failures, both cell probes, source/model
copies, actual records, bounded decisions and producing runtime observations.
Its replay independently parses the counterexamples, checks every expected
public test and reference record, and preserves the physical rejection:

```text
python evidence/E0043-sram-physical-integration/local-netlist/verify.py --output build/sram-local-netlist-replay
```

Use a new output directory. The retained replay passes; it audits these
completed runs without rerunning the long simulations.
