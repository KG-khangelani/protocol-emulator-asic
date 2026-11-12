# Portable SRAM physical qualification preparation

The isolated official setup reproduces the exact D43 power-grid database in
39.324 seconds, under a 300-second bound. It runs from the staged project root
using the official launcher's relative paths and native plugin discovery.
All resolved physical settings match full trial 03; the design-directory
anchor changes from the explicitly supplied project root to `src`.

Six deliberate resolved-configuration faults are rejected: missing real macro,
wrong fast library, waived DRC, extra RTL, substituted flow and relaxed clock.
The pinned container identity and read-only PDK mount are observed. Doctor and
all 114 repository checks pass.

Three launcher preparation errors are retained. A first successful native pilot
used sorted geometry keys, creating the same wires in reversed supply-net order;
its binary-identity audit failed. Preserving the original VPWR/VGND creation
order restores the exact earlier database hash. Neither sources nor physical
wire geometry changed during that correction.

The archive also freezes the completed extracted timing stage of buffered full
trial 03: every slew, capacitance and fanout violation count is zero at all
three declared model sets. Setup/hold margins remain positive; detailed-routing
DRC and antenna counts are zero. This is a completed-stage snapshot while later
manufacturing checks remain in progress, not a complete qualification.
The fast model set remains standard cells at -40 C with SRAM at -55 C.

```console
python evidence/E0043-sram-physical-integration/official-staging/verify.py --output build/sram-official-staging-replay
```

The separate `gds-sram` workflow stages the exact candidate and original pinned
toolchain. Full physical checks, ten official prechecks, eighteen actual-netlist
public groups, downloaded-archive audit, production integration and publication
remain required. The initial Verilator netlist attempt stops on 84 ignored
cell-model specify warnings and 28 intentionally unloaded clock-buffer outputs;
a separately declared retry handles only those two categories on identical
netlist/library bytes. The complete local netlist results are still pending.
