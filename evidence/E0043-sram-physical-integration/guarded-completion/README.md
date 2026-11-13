# Native guarded trial 05 completes with the original contact-rule failure

The full native flow reaches all 84 stages and returns failure after
9,381.393 seconds within its unchanged 10,800-second limit. It is not a
timeout. Magic reports 36 contact findings, byte-identical to official
run43320295442. Every other final physical metric matches that official run,
including passing timing/electrical limits, power, routed DRC, antenna and LVS.
The circuits match uniquely. The original generic `FAILED_OR_INCOMPLETE`
receipt remains unchanged; the separate completion review records the known
completed rejection.

The archive retains 927 native text reports, inputs, configurations, state
records and logs. Another 57 generated views are indexed by size and digest.
The exact checked GDS is already retained in the guarded official failure's
geometry archive; the routed database and netlist are in the guarded LVS
diagnostic. This is a report replay, not a new physical rerun or acceptance.

```text
python evidence/E0043-sram-physical-integration/guarded-completion/verify.py --output build/guarded-completion-replay
```

The separately scheduled original/corrected full-layout diagnostics and the
fresh corrected official run remain distinct attempts with their own bounds.
Production remains unchanged.
