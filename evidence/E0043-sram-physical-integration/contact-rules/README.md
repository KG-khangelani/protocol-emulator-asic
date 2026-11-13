# SRAM contact-rule diagnosis

The unmodified pinned SRAM produces **32 Magic contact-enclosure findings**
in 364.774 seconds with the seven vendor import patterns. The earlier
120-second timeout remains retained. Measuring every reported location in
the original GDS finds twelve 60 nm enclosures inside DigiBnd and twenty
10 nm enclosures inside SRAM. Coincident contact instances at abutting
corners are counted as one piece of geometry, with their multiplicity retained.

The pinned rule implementations disagree. The foundry layout document's
printed page 58, section 8.1.2, specifies 50 nm inside DigiBnd; Magic applies
70 nm. The pinned KLayout deck specifies 6 nm inside SRAM; Magic applies
20 nm. The PDF's SRAM section says **work in progress** and does not establish
that 6 nm value. Its printed page 15 requires a 5 nm drawing grid. The next
legal grid distance at or above 6 nm is 10 nm; Magic rounds its check upward.
The complete pinned PDF and both inspected page renders are retained.

Primary references:

- [Pinned foundry layout rules](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l/libs.doc/doc/SG13CMOS5L_os_layout_rules.pdf).
- [Pinned KLayout contact parameters](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l/libs.tech/klayout/tech/drc/rule_decks/sg13cmos5l_tech_default.json) and [contact checks](https://github.com/IHP-GmbH/IHP-Open-PDK/blob/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008/ihp-sg13cmos5l/libs.tech/klayout/tech/drc/rule_decks/feol/5_14_cont.drc).
- [Magic 8.3.677 rule scaling](https://github.com/RTimothyEdwards/magic/blob/8.3.677/drc/DRCtech.c), `drcScaleDown`, explicitly rounds distances upward.

A copied Magic technology changes exactly two files: derive contact-specific
regions from real GDS markers, retain 70 nm outside the special regions,
apply 50 nm inside DigiBnd outside SRAM, and use the pinned KLayout 6 nm SRAM
value. All three original low-voltage contact types are covered. The existing
70 nm SRAM directional check and every other rule remain unchanged. No macro
geometry is edited or excluded, and no report is filtered for acceptance.
The complete original SRAM then has **zero full-rule Magic findings** in
450.990 seconds under the separately declared 1,200-second bound.

All 48 contact cases are checked with both original and proposed rules.
They cover both sides of each boundary, all three contact types, marker
priority, remote/partial/holed markers, the unchanged directional rule and an
unrelated undersized Metal2 shape. The first control attempt is retained as
rejected: it incorrectly expected an off-grid 6 nm shape to pass after Magic
snapped it to 5 nm. The follow-up preserves every polygon and rule, corrects
that documented off-grid expectation, and passes. Its 5 nm negative and
10 nm positive on-grid cases are unchanged.

The portable startup wrapper stages the exact tested two-file correction
only for `Magic.DRC`. It pauses background checking during import and restores
it afterward; the original synchronous full-check script and all its report
handling remain intact. A native rehearsal reproduces every retained control
finding and confirms other Magic stages use the original technology. The first
wrapper attempt failed because Magic cannot dispatch a renamed `gds` command;
the corrected wrapper uses execution traces and preserves the native command.
Three earlier preparation failures are also retained.

The **111-file archive** is 1,252,155 bytes. Windows audit and fresh native
Linux replay pass. The native replay checks all control findings, startup
scope and rejection of a changed reference file before staging. The pinned
PDK stays read-only; its bulk libraries are not copied into this archive.
Doctor and all 116 repository checks also pass in the pinned workbench.

```console
python evidence/E0043-sram-physical-integration/contact-rules/verify.py --output build/sram-contact-replay
# In the pinned physical image with the pinned PDK mounted read-only:
python evidence/E0043-sram-physical-integration/contact-rules/verify.py --output build/sram-contact-native --native
```

This is a scoped diagnostic. Both initial 20-minute and separately declared
one-hour complete-layout trials remain incomplete. The one-hour runs reach
full DRC but time out without reports; their original receipts are retained
in `full-layout-followups.tar.gz` and pass `verify_followups.py`. Do not extend
these attempts while the corrected official workflow is already running.
Fresh full-flow qualification, official precheck and the corrected submitted
netlist tests remain required. Production is unchanged and G2 remains active.
