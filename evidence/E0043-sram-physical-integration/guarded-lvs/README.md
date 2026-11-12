# E0043 - Corrected routed design passes native LVS diagnostic

A separately declared, 600-second diagnostic runs the original native Magic
extraction, illegal-overlap checker, Netgen LVS and LVS checker on trial 05's
unchanged routed design. It passes in 60.813 seconds: both circuits have 4,717
nets and 4,684 devices, all 45 top-level pins including supplies match, and
LVS errors and illegal overlaps are zero. The original failed design had 17
fewer layout nets. The first diagnostic launch fails because its new run
directory had not yet been created; that attempt is retained.

This retains the original flow's DEF/LEF extraction and black-box SRAM
comparison. It checks the integrated connections, not the vendor macro's
internal transistor circuit. Full GDS DRC, the complete physical run, official
precheck and actual submitted-netlist tests remain separate gates.

The archive retains 137 files: native reports, exact extracted and reference
circuits, routed views, configuration, source copies, initial/final states,
runner, producing runtime and the launch failure. Verify into a new directory:

```text
python evidence/E0043-sram-physical-integration/guarded-lvs/verify.py --output build/guarded-lvs-replay
```

Then use the pinned physical image
`sha256:b4f7c1e0f99a5d5b419571277a3e93bac37ea22eb7e4af3787d59927b73067c5`,
the repository at `/workspace`, and the pinned PDK at `/pdk`, mounted read-only:

```text
python3 evidence/E0043-sram-physical-integration/guarded-lvs/replay_native.py --directory /workspace/build/guarded-lvs-replay
```

Native replay repeats the circuit comparison using its original setup
environment, then checks all 43 public pin rectangles in the retained final
routed database: zero pin/power violations. It does not repeat extraction.
An initial direct replay omitted Netgen's setup environment, reported setup
errors and changed the normalized antenna-device count. The strict device
check rejected it; its script, output and failure are retained separately.
The corrected native replay reproduces the original counts with no setup
errors and zero LVS errors. Full physical qualification remains open.
