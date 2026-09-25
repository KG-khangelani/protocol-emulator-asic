# Pinned verification workbench

This container is the project's fast Linux development environment. It gives a
Windows, Linux or CI user the same dated OSS CAD Suite and hashed Python
packages. It runs lint/simulation/formal/synthesis tools; it is **not** a local
replacement for the official Tiny Tapeout CMOS5L qualification workflow.

From PowerShell at the repository root:

```powershell
.\tools\workbench.ps1 Setup
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 All
```

The first build downloads the 737 MB OSS CAD Suite archive and can take several
minutes. Docker caches the verified result. `Doctor` shows what is installed;
`All` verifies every installed version, then runs static checks, Verible lint,
RTL tests and generic synthesis. Individual commands are `Check`, `Lint`,
`Test`, `Formal`, `Synth`, `Evidence`, and `Shell`. Until the M0 property
harness lands, `Formal` deliberately returns `NOT_EVALUATED` and a nonzero
status; it is not included in `All` yet.

On Linux or WSL, use the equivalent `./tools/workbench.sh` commands. Both
wrappers mount this repository at `/workspace`, so generated output appears in
the normal ignored `build/` and `test/sim_build/` locations.

## What is locked

- Python 3.11 base image by OCI digest.
- OSS CAD Suite `2026-07-29` Linux x64 archive by SHA-256.
- Verible `v0.0-4296-g0f262651` static Linux x64 archive by SHA-256.
- Direct and transitive Python packages with hashes.
- Small Debian runtime packages by exact version.
- Official CMOS5L action, support-tools, LibreLane and PDK identities in
  `toolchain.lock.json` (qualification remains a separate GitHub workflow).

The local image tag is a convenient name, not an integrity identity. Evidence
must also record the built image ID and the lock file/source commit.

The cocotb startup line says Python 3.11.9 because that version string was
compiled into its binary wheel. Loader tracing confirmed that the simulation
loads `/usr/local/lib/libpython3.11.so.1.0` from the pinned Python 3.11.16 base;
`Doctor` checks the actual command-line runtime.
