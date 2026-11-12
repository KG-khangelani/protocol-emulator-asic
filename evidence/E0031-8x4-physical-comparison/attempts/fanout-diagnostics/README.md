# Bounded local fanout diagnostics

All runs use the exact pinned LibreLane image, PDK, E0030 RTL and official 8x4
pin DEF. They stop after post-route timing: Magic DRC, LVS, official precheck
and public netlist tests are not part of these local diagnostics.

| Trial | P final fanout / antenna violations | compact10 final fanout / antenna violations | Disposition |
|---|---:|---:|---|
| Fanout constraint 8 and clock cluster size 8 | 1 / 0 | 3 / 0 | Rejected |
| Add 100 um clock buffer spacing; normal antenna repair | 1 / 0 | 0 / 0 | Shared official retry; compact10 fallback |
| Same spacing; detailed-route jumpers only | 0 / 2 | 0 / 0 | Rejected |

All rows have zero final routing DRC, slew and capacitance counts and positive
setup/hold at all three extracted corners. See result.json for exact values.
A successful tool exit is not physical acceptance.

The clock-stage-only report checks the nominal corner freshly. Its preceding
CTS run carries inherited metrics, which must not be presented as newly
measured post-CTS results. Final diagnostics retain fresh all-corner reports.

Antenna-loads.json and its read-only inspection script identify the remaining
P load increase: seven functional loads become eleven when detailed routing
adds four antenna diodes. ODB hashes identify both inspected databases.
Full databases stay in the ignored build directory; official raw artifacts
and their immutable hashes are retained separately.

Both source hashes match E0030. Resolved configurations agree between variants
after normalizing their design-directory paths. Command manifests, logs,
resolved configurations, raw metrics, timing reports and checksums are retained.
The early Windows host test-import error is in doctor-check.json; the pinned
workbench's repository/model/evidence checks pass.
