# E0043 - Portable guarded physical staging

The D45 staging path completes its native pilot in 41.669 seconds under the
unchanged 300-second pilot limit. Plugin discovery starts from the staged
project directory with `PYTHONPATH` removed. The corrected power geometry and
all 43 public pin rectangles reproduce the ongoing full trial's exact database
hash. Both supply-grid checks pass, and the new pin guard reads that database
without changing it. This is a staging result; complete physical qualification
remains open.

Eight actual resolved-configuration changes are rejected: a missing macro,
the wrong fast timing library, disabled DRC, an extra RTL source, the removed
pin guard, a relaxed clock, missing vendor import patterns and broadened
vendor import patterns. The pinned vendor setup hash and all real macro views
are checked. Every original Classic stage remains, with four project stages
for power connection, power checking, input buffering and fixed-pin checking.

The original 369-file archive retains the staged sources, native logs,
configuration, actual databases, verification controls and producing runtime.
The exact fixed-pin DEF template is retained separately. Source provenance
records the development tree on 679a432; it does not claim a clean CI run.
The frozen specification predates its final explanatory wording update.

Verify and extract into a fresh directory:

```text
python evidence/E0043-sram-physical-integration/guarded-staging/verify.py --output build/sram-guarded-staging-replay
```

Then use physical image
`sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5`
with this repository at `/workspace` and the pinned PDK volume at `/pdk`,
mounted read-only:

```text
python3 evidence/E0043-sram-physical-integration/guarded-staging/replay_native.py --directory /workspace/build/sram-guarded-staging-replay
```

Native replay uses the frozen staging auditor, repeats all eight configuration
controls, checks actual vendor files, and reruns the frozen geometry checker
on the retained database. It requires the same PDK revision; it does not
require the original build directories. The complete routed manufacturing,
official precheck and submitted-netlist gates are separate requirements.
