# E0041 - Bounded clock-routing diagnosis

The original D39 physical run43249867361 failed global routing. Its post-CTS
database contains sixteen clock trunk nets with the CTS_NDR_0 extra-spacing
rule. The pinned router disabled that rule on seven clock nets before GRT-0228.

The [predeclared diagnostic](../../docs/specs/g2-clock-routing-diagnostic.md)
copies that database and removes only those sixteen net-to-rule assignments.
Exact before/after DEF comparison preserves all cells, placement, pins and
connections. Runtime, PDK, footprint, clock, routing layers, 30% adjustment,
50 overflow iterations and four threads remain matched. Removing clock spacing
is an intentional diagnostic change, not an unchanged-flow qualification.

The first actual route **times out after 1,200.029 seconds**, at extra
iteration 40/50. No final congestion report or routed output is produced.
It is **incomplete and not qualified**, not evidence that the change succeeds
or fails physically. The separately declared 2,400-second follow-up completes
in 867.548 seconds, using the identical modified database and matched settings.
It avoids GRT-0228 but finishes with **159,781 total overflow**. Metal3 demand
is 395,330 against 259,924 resources, or **152.09%**. The command exits zero
because the inherited configuration allows congestion; this is not acceptance.
Stop the clock-spacing-only branch and investigate a materially smaller memory
implementation. Neither attempt qualifies a physical setup.

A preceding preparation assertion failed because the DEF writer placed the
NDR assignment inline, while the checker expected a whole line. Both DEF
outputs and the sixteen changes were correct. The retained original runner
and failure precede the corrected exact-token comparison; no routing began in
that preparation attempt. The first spec snapshot also retains a function-name
typo, corrected to `Graph2D::getCostNDRAware` in the live specification without
changing the experiment.

`attempt-1200s/` retains the original scripts, source/database hashes, both
compressed DEF files, exact edit, settings, command, input audit and full
captured process output. The interrupted per-step log was still buffered;
`run.log.gz` is the outer process output that actually captured progress.
`upstream/` retains two exact Git blobs from the pinned router, with URLs and
hashes. Its edge-usage guard and NDR penalty both use a factor of 100, so the
reported 1704/1700 is not a chip-area margin.

`attempt-2400s/routing.tar.gz` retains 25 exact files, including the actual
output database, DEF, guides, logs, metrics, original scripts and settings.
Its input DEF pair and modified input database hash match the first attempt;
duplicate final views are omitted. Timing values inherited in the resumed
state are not fresh routed signoff. No detailed routing, precheck or netlist
protocol test was run by this diagnostic.

```text
python evidence/E0041-clock-routing-diagnostic/verify.py
```

The replay checks retained bytes, the exact sixteen assignments, first timeout
and final congestion. It does not run routing or qualify a new physical setup.
