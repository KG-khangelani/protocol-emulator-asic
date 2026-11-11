# D26 - Resolve the actual-program claim with proved loop invariants

Date: 2026-11-03 UTC. Status: written normal-transaction proof, experimental RTL.

E0024's direct444-step actual-program attempts remain inconclusive. Their
large unrolled models repeatedly rediscover the same loop schedule and loaded
image. In one bounded attempt, state those facts as assertions over the actual
DUT, then prove them together with the original public properties. Keep the
[frozen attempt contract](../specs/spi-program-invariant-attempt.md), exact
firmware, public loading sequence and external input assumptions unchanged.

The new assertions cover every actual stored byte during public loading,
length/ready, payload/result lifetime, per-loop PC/waits/counts, phase flags,
partial TX/RX state and synchronizer history. They constrain no internal state
by assumption and substitute no instruction memory or executor. Formal-only
output taps have checked inverse transformations. The generated model retains
all412 actual state bits across engine110, program store261, data store25 and
synchronizer16. Its only8 assumptions are the unrolled original rising-edge
MISO conditions;82 assertions include original public goals and strengthening.

Before the single formal run, finite Icarus preflight checks all assertions
and the timing premises on the real instrumented top for four concrete byte/
order cases. Initial preflight compilation fails because generated readout
assignments and simulation logic precede declarations under strict net typing.
Reordering those generated declarations changes no DUT behavior; retain the
failure. No proof job was spent on that compilation issue.

Freeze one prove configuration: depth12, Z3,180-second wall limit. The single
local job passes in7.103s, with base0..11 and successful induction step9.
This is a proof of the written actual loaded-program properties under the
fixed driver and sampled digital input premise, including the subsequent reset
and quiescent tail. It is stronger than a12-step bounded pass. It is not a new
444-step BMC, arbitrary-firmware termination or complete SPI qualification.
The four preflights are finite witnesses, not formal reachability covers.

Record the distinction in E0025. Preserve E0024's two90-second timeouts,
earlier E0023 timeout and every counterexample without relabelling them. CI
replicates exactly this configuration/limit and rejects a missing, inconclusive
or non-inductive result; no adaptive proof retry or budget increase occurs.

Next, independently test property/assumption sensitivity and actual firmware
negative controls/reachability before considering production promotion. No
new ISA, production RTL, physical run, four-mode SPI, H1-H4 or owner-fluency
promotion follows. Keep PR11 draft/unmerged and PR8/compiler deferred.
