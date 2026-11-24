# D52 — Deliver the powered cold loader

On 24 November 2026 the owner directed the project to prioritize engineering
and to resume G6 only upon their explicit request. Keep its existing record
for that time. Prioritize the user-invocable digital loader from D51 and the
January competition filing. Physical testing depends on an equipped fixture.

## First engineering acceptance

Use the v0.1.0 UART receiver as the starting image. Run the released versioned
binary, metadata and load plan against the production public interface. Before
the first program edge, isolate the peer, reset the selected chip, verify every
byte, commit the length, verify payloads and hand over the pins and clock in
the order recorded in E0049. Receive `96 69` using the released host rules.
The simulator must observe pin direction, clock edges and peer isolation
independently of the controller's requested state.

Inject a corrupted byte, an idle-high peer whose link stays closed, an
unscheduled clock and an unordered selector handoff. Each must stop before a
successful launch can be reported. Check the 55 G3 and 20 applicable G5
records against their archived originals. Use the existing protocol runtime
sequencers. Keep the separate 1,160-case I²C replay available if they change.
Budget one engineer and 4–8 hours for this digital scope. Keep outputs in fresh
directories on H: and preserve the twenty qualified inputs. Board measurements
require independent evidence on the named fixture.

[Council disposition](0051-review-council-next-steps.md) · [Cold-start contract](../research/council-2026-11-24/next-experiments.md)
