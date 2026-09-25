# E0009 — Fresh Windows clone verification

A new clone of the public GitHub repository at commit
`5becc62e4334809a9f75c0d4d87fe3a176c72ebc` ran the complete locked fast
ladder through `tools/workbench.ps1` on Windows 11. All seven stages passed:
doctor, static checks, lint, Icarus, Verilator, formal, and generic synthesis.
The clone remained Git-clean because generated results stayed under ignored
paths.

No native `make`, Icarus, Verilator, Verible, Yosys, SBY, Z3, or Boolector
command was discoverable on the Windows host. Docker supplied the Linux/amd64
workshop and all EDA tools. This directly checks the user-facing promise that a
fresh Windows clone can run without native Windows EDA installations.

## Cross-platform byte check

An exploratory clone at the preceding commit passed functionally but revealed
that Windows CRLF checkout conversion changed source-file SHA-256 values versus
Linux CI. Commit `5becc62` made LF the canonical repository text format, and
this accepted rerun followed that correction.

The RTL, configuration, metadata, gate-level tests, and GDS workflow now have
the exact same byte hashes in this Windows/Docker run as in Linux CI E0007.
That distinction matters: Git identity already protects repository content,
while the matching SHA-256 values additionally show the tools read identical
bytes on both hosts.

## Evidence boundary

`manifest.json` records the clean commit, source hashes, tool versions,
commands, and stage results. The retained JUnit results, formal statuses, and
generic netlist support the summary. The local Docker image was a previously
built image with the qualified tag and exact-version doctor checks; E0007
separately proves that CI can build the image from repository inputs.

This is fast digital verification, not CMOS5L physical proof. It establishes
fresh-clone operability and cross-platform input identity, but not placement,
routing, timing, DRC/LVS, gate-level mapping, or fabricated-silicon behavior.
