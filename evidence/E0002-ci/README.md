# E0002 — First successful CI baseline

GitHub run [35792901577](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/35792901577)
passed static checks, the M0 GPIO RTL regression, and generic Yosys synthesis
for source commit `91195673d7a37b4257b01c5bf6c4f5cf6a817582`.
The official docs workflow also passed. Job and artifact metadata are retained
in `result.json`; the successful checks step reported all three stages PASS.

The uploaded verification artifact contains the runner's manifest, logs,
JUnit result, FST waveform and generic synthesis output. Its SHA-256 is
`6b551bb7668acb29c62d2e60f2820cfc719586bd1d07926e80d1b25ac7e73439`.
The Actions artifact expires on **21 December 2026**, before submission.
Download and archive it durably before then. The browser download attempted
during setup timed out, so this repository retains metadata, not the binary.

This supersedes E0001's environment blockage for CI execution; it does not
invalidate E0001's observation about the local setup runner. No IHP physical
fit, gate-level, formal, FPGA or clean-rerun evidence has been produced.
