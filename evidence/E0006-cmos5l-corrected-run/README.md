# E0006 — Corrected official CMOS5L run

GitHub run [36111852179](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36111852179)
tested commit `1bcb92ad038a0105cb61158fa104c55aeeb3cb35` on 25 September
2026. GDS generation, gate-level regression, and all Tiny Tapeout prechecks
passed. The workflow's recorded result is **PASS**.

## What passed

| Stage | Plain-language question | Result |
|---|---|---|
| GDS build | Can the RTL be converted into placed and routed CMOS5L geometry? | PASS |
| Gate-level test | Does the generated cell netlist still satisfy the two M0 pin-behavior tests? | PASS |
| Precheck | Does the layout satisfy the nine Tiny Tapeout submission checks? | PASS |

The gate-level run executed `reset_wrap_hold_and_resume` and
`seeded_control_and_input_noise` for 31,220 simulated ns in total. This closes
the E0003 source-list failure: the required `ihp_dff_r` UDP model was present,
the netlist elaborated, and both tests ran. The retained JUnit summary is
`gatelevel-results.xml`; the complete waveform remains in the downloaded
artifact and is identified by SHA-256 in `result.json`.

The physical numbers match E0003: 58 mapped synthesis cells (803.7792 µm²),
80 final standard cells (1,166.66 µm²), and 0.129282% standard-cell
utilization. Worst reported setup slack was +13.585833 ns and worst hold slack
was +0.172078 ns at the 20 ns target. Route DRC, Magic DRC, LVS, antenna,
setup, and hold violation counts were zero. All nine prechecks passed.

In plain language: the generated layout fits, the reported timing margins are
positive at the requested target, and a simulation of the generated gates
preserves M0's tested behavior. It does **not** prove fabricated-silicon
behavior, a maximum clock frequency, or any protocol-emulator capability.

## Reproducibility observation

E0003 and E0006 produced equally sized GDS files and identical recorded
physical metrics, but different whole-file SHA-256 hashes. A GDS-record-aware
byte comparison found 256 differing bytes, all inside the one `BGNLIB` and 31
`BGNSTR` creation/modification timestamp records. No non-timestamp record
differed, so the recorded geometry content is byte-identical after excluding
those timestamps.

This is why the evidence records both content hashes and the semantic
comparison. A hash answers "are these files exactly the same?"; it cannot by
itself explain whether a difference changed chip geometry.

## Remaining boundary

This run used the intended action, support-tool, LibreLane, and PDK revisions,
but the workflow still selected the Tiny Tapeout action through the mutable
`ihp-cmos5l` branch name. M0 therefore remains open until those inputs are
pinned in the repository and the pinned flow passes from a clean checkout.

Large downloaded artifacts remain under ignored
`build/artifacts/E0006-corrected-run-36111852179/`. GitHub retains the original
artifacts until 24 December 2026. Selected metrics, raw precheck output, job
results, identities, hashes, and limitations are retained here.
