# E0043 - Corrected GDS passes the complete KLayout rule-deck diagnostic

Trial 05's unchanged GDS passes the pinned CMOS5L KLayout rule deck in
550.779 seconds under the declared 900-second diagnostic bound. Its native
report contains the correct top cell, 332 rule categories and zero violations.
The command matches the pinned official precheck's CMOS5L check, apart from
output paths. No rule, geometry or acceptance option is changed.

This independent diagnostic uses KLayout 0.30.12 from the pinned physical
image. It does not replace the separate official precheck environment, the
other nine prechecks, Magic DRC, the complete physical flow or submitted-netlist
tests. Those gates remain required.

The original result, complete report/log, runner, source reference, actual
runtime and all pinned rule-directory file hashes are retained. The reference
copy differs from the primary precheck source only by one extra trailing LF;
both identities and the direct source comparison are recorded. Replay derives
the exact command from its frozen functions and checks the actual GDS against
the complete retained layout in the adjacent `guarded-lvs` archive:

```text
python evidence/E0043-sram-physical-integration/guarded-klayout/verify.py --output build/sram-klayout-replay
```

For the native report reader and every retained rule-file hash check, add
`--native` in physical image
`sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5`,
with the repository at `/workspace` and the pinned PDK mounted read-only at
`/pdk`. Both retained replays pass. This audits the completed diagnostic;
it does not repeat the full DRC execution.

The first Windows replay converted a recorded Linux path to Windows separators
and failed its strict command comparison. That preparation failure is retained;
the corrected replay preserves the recorded path when reconstructing arguments.
