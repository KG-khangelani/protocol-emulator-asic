# D30 - Retain the mode1 saving and measure a general timed GPIO operation

Date: 2026-11-12 Johannesburg. Status: local capacity study complete; remote
qualification and research publication pending.

E0029 corrects the first-CS-edge oracle boundary while preserving its full
idle/setup/hold contract. Fixed low SCK can provide mode1's initial idle interval,
saving one redundant SET: nine words. Mode3 still requires ten in the examined
family. All6,920 declared schedules and108 publicly loaded eight-word deletion
controls found no fitting phase1 program. This establishes no ISA lower bound.

Retain the actual eight-word store and unchanged candidate/production RTL.
Keep E0028's held mode0/2 proof and its counterexamples as regression gates.
Do not enlarge storage merely because the tested family failed to fit.

The next bounded experiment should measure a general masked GPIO value update
with a configurable delay before or after the update. Preserving direction
would let ordinary SET initialize output enables. In the common explicit-idle
phase1 template, combining ASSERT-CS plus WAIT22 and WAIT23 plus SET-clock
could remove two words. A proposed eight-word schedule is:

1. SET idle clock and CS, with direction.
2. Update CS low, then delay23 ticks.
3. LOOP three body instructions, eight iterations.
4. DRIVE the bit and leading clock.
5. Delay24 ticks before updating the trailing clock.
6. SAMPLE with the existing delayed capture count23.
7. SET CS high and idle clock.
8. HALT.

This is a scheduling hypothesis, not measured RTL behavior. Define precise
count/entry/terminal semantics before implementation. Audit all formerly legal
encodings: ordinary SET's ignored high bits cannot simply be reclaimed while
claiming full compatibility. A previously invalid opcode region is a possible
alternative. Sharing wait state may reduce cost, but no zero-flop or area claim
is justified without measurement.

Use isolated generated variants and the unchanged loader, store and external
oracle. Compare timing semantics, zero/max delay, pauses, reset and loader abort;
run both simulators and scoped legal-legacy refinement with falsification
controls. Measure generic whole-chip cells/state against the existing compact
and expanded-store references before selecting a direction. Physical fit/timing,
full four-mode qualification and owner fluency remain separate gates.
