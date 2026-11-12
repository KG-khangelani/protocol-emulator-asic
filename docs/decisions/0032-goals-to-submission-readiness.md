# D32 - Focus the remaining work on submission readiness

Date: 2026-11-12. Status: adopted planning direction at the owner's request
to set worthwhile goals. No new chip or owner-fluency gate is passed here.

The [goals](../goals.md) prioritize physical feasibility, shared-core protocol
coverage, a usable toolchain, reproducible final closure, one bounded novelty
experiment and independent owner understanding. The first engineering goal is
G1; later goals have explicit completion checks and planning targets.

## Evidence that changes the order

D31/E0030 establishes an eight-word phase1 candidate and a generic cost saving,
but no mapped or routed advantage. I2C and combined production qualification
remain missing. Further local instruction compression therefore has less
immediate decision value than a complete-chip physical measurement.

The latest [S1 observation](../sources.md) also supersedes the old allocation
assumption. G1 must reconcile the checked-in 6x4 baseline with the current 8x4
rules before treating a new physical result as a submission candidate.
Historical E0003/E0006/E0010 results retain their original conditions.

## Decision and bounds

1. Audit and qualify the updated physical setup, then compare P and compact10
   under matching conditions. The 50 MHz target remains an experimental
   condition unless a later decision explicitly changes it.
2. Complete the declared UART/SPI/I2C workloads on one core. Specify I2C first,
   and preserve UART service and SPI input-hold boundaries.
3. Deliver a small assembler and reproducible examples before considering a
   larger compiler.
4. Start physical validation early; aim for a January 4 candidate freeze and a
   January 11 submission-ready package. These are planning targets.
5. Allow one two-working-day firmware-only novelty experiment after mandatory
   protocol coverage. Defer it if prerequisite work runs late.
6. Keep owner learning independent under D8; no automated fluency promotion.

This decision records the migration requirement, not a qualified change to
RTL, metadata, flow pins, the machine-readable evaluation contract or memory
capacity. G1 must change and validate those together. A planning-only commit
does not require a new release tag; alpha.4 remains the latest qualified release.
Actual competition submission and hardware spending remain separate decisions.

## Review trigger

Reconsider the direction after the first matched physical result, a missing
general capability exposed by I2C, a mandatory regression failure, or a missed
planning target. Preserve the failed result and write the reason for any scope,
clock, capacity or schedule change. Do not make novelty depend on discarding
negative evidence or claiming unmeasured performance.
