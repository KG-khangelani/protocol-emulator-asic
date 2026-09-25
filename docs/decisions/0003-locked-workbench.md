# D3 — Use a locked Docker workbench for the fast verification lane

Date: 2026-09-25. Status: adopted for M0.

Need: Windows should be able to run the same fast chip-development tools as CI
without depending on separately installed native EDA packages. A version name
alone is insufficient when daily tool bundles and transitive Python packages
can change.

Decision: use a Linux/amd64 Docker image with its Python base pinned by OCI
digest, OSS CAD Suite and Verible archives pinned by SHA-256, Debian packages
pinned by exact version, and Python dependencies pinned with hashes. Make
`toolchain.lock.json` the machine-readable ingredient record and make `Doctor`
fail inside the container if observed versions differ. Keep the official
Tiny Tapeout CMOS5L workflow as a separate physical-acceptance lane.

Consequences:

- Windows users need Docker Desktop, PowerShell and Git, but no native Icarus,
  Yosys, Verilator, Verible, SBY or solver installation.
- The first image build downloads a roughly 737 MB EDA archive and is currently
  limited to x86-64 hosts.
- A narrow Verible `module-filename` waiver preserves Tiny Tapeout's required
  `project.v` filename and unique `tt_um_*` module name; other default rules
  remain active.
- The workbench can support lint, simulation, formal checks and generic
  synthesis, but it cannot establish CMOS5L area, routing, timing or precheck.

Rejected for this step: treating whichever native tools happen to be installed
as the reproducible baseline, or duplicating the official physical acceptance
flow locally before the upstream action is pinned and qualified.
