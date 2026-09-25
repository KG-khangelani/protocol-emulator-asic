# E0008 — Upstream drift canary baseline

GitHub run [36120280373](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36120280373)
tested the read-only upstream canary at commit
`fcbfafb6e4577b00da57a67807aa5ba58ffc8302` on 25 September 2026. The
workflow completed successfully and uploaded its JSON observation.

The canary compared the live Tiny Tapeout
`tt-gds-action@heads/ihp-cmos5l` ref with the action commit qualified in the
project lock. Both resolved to
`3412659307918422f3f0727917cf9b499aaca588`, so the observation state was
**CURRENT**. It also recorded `acceptance_environment_changed: false`.

In plain language: the upstream pointer had not moved at the observation time,
and the monitor did not alter our workshop. If it moves later, the canary will
report **DRIFT** and retain the old qualified pin until a human reviews and
deliberately changes it. A network or API failure is **ERROR**, not CURRENT.

This result proves that the scheduled workflow can check the ref and preserve a
machine-readable observation. It does not prove that the upstream ref will stay
unchanged, that a future upstream commit is good or bad, or that the separate
physical flow passes. `observation.json` is the original remote output;
`result.json` records its run and artifact identity.
