# D28 - Use delayed sampling only under an explicit hold contract

Date:2026-11-12 Johannesburg. Status: scoped reference and dual-simulator result.

E0027 freezes all four mode edge schedules with idle clock before CS,25-clock
CS setup/hold, both orders and two separate input profiles. A naive mode2
polarity edit can return the correct byte while violating the CS boundary.
Payload equality therefore cannot replace waveform/boundary checks.

Existing SAMPLE(delay23) can absorb the trailing WAIT at H25. The clock schedule
is unchanged, but RX consumes raw S+22 rather than raw S. This is valid under
the held-response envelope and fails the edge-only stress witness. Keep these
contracts and results separate; E0025's exact-sample proof does not qualify
the delayed firmware.

The saved word makes room for explicit idle setup. Modes0/2 fit8 words and
pass the scoped public-pin screen on both simulators with unchanged compact
RTL. The examined phase1 schedules require10 held-data words or11 exact-data
words. These are constructive program counts, not ISA lower bounds.
Do not enlarge the store or add a protocol-specific instruction on that basis.

Next formally qualify the fitting delayed-capture programs under their written
hold premise. Also investigate phase1 schedule compression or a measured general capacity tradeoff.
Keep production RTL, compiler, physical and learning gates unchanged.
