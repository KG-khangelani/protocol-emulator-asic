# Toolchain and reproduction

## Source baseline

Official template: `TinyTapeout/ttihp-verilog-template`, `cmos5l`, commit
`b86a2a781484bcab7ba522dc5de540086695a430`. See `upstream-template.json` for
the verified file inventory. `src/config.json` is preserved byte for byte.

The upstream devcontainer had `PDK=ihp-sg13g2` while its CMOS5L workflow and
test harness used `ihp-sg13cmos5l`. The devcontainer variable is aligned with
the latter. That edit still requires a container/physical build to validate.

## Fast local loop

The supported local path is `tools/workbench.ps1` on Windows or
`tools/workbench.sh` on Linux/WSL. It builds a Linux/amd64 Docker image from:

- Python 3.11.16 base image pinned by OCI digest;
- OSS CAD Suite `2026-07-29` archive pinned by SHA-256;
- Verible `v0.0-4296-g0f262651` archive pinned by SHA-256;
- exact Debian package versions; and
- direct and transitive Python packages pinned with hashes.

`Doctor` checks installed outputs against `tools/workbench/toolchain.lock.json`
and fails on a missing or different version. `Check` performs static consistency
only. `Lint` runs Verible with one documented Tiny Tapeout filename waiver.
`Test` invokes cocotb/Icarus, while `TestVerilator` runs the same oracle through
an independently implemented simulator; both reject missing, empty, skipped or
failed JUnit results. `Synth` runs generic Yosys and leaves `build/synthesis.log` and
`build/synth.json`. `Evidence` records source hashes, exact commands, versions
and stage status. `Formal` is explicitly `NOT_EVALUATED` until the M0 property
harness lands; a missing proof must not appear as a pass.

## Physical gate

1. Push the intended source revision to the project repository.
2. Wait for `test` to pass and inspect the uploaded verification artifact.
3. Trigger **Actions → gds → Run workflow** on that revision's branch.
4. Inspect `gds`, `precheck` and `gl_test` independently; retain failure logs.
5. Download/archive artifacts; identify the input commit and resolved action,
   LibreLane, PDK and container versions.
6. Record mapped cell area, physical utilization, worst setup/hold slack,
   violation counts, final GDS SHA-256 and artifact/run URLs.
7. Rebuild from a clean checkout using the same resolved inputs. Compare
   functional acceptance and timing/area. Document expected tool nondeterminism
   instead of assuming every physical artifact must be byte-identical.

The Pages viewer is disabled during bootstrap and is not an acceptance gate.
The FPGA job remains manually available; no board compatibility is claimed.

For local hardening, consult the official guide in `sources.md`, but derive
the PDK and tooling from the **CMOS5L action branch** used by this repo. The
general guide still shows another IHP PDK and is not a drop-in process lock.
Do not blindly replace `ihp-sg13cmos5l` with `ihp-sg13g2`.

### First observed physical environment

E0003 resolved the CMOS5L action branch to action commit
`3412659307918422f3f0727917cf9b499aaca588`, Tiny Tapeout support tools
`d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`, LibreLane `3.1.0.dev3`, and
IHP Open PDK `2bbec755dc67ca3db0261c3d6163e15735d66710`. The GDS and precheck jobs
passed. The gate-level runner used Python 3.11.16 and Icarus 13.0, but failed
at elaboration because `test/Makefile` omitted `sg13cmos5l_udp.v`. That source
list is corrected, and the exact archived netlist now passes locally with the
recorded PDK model; official rerun acceptance is still pending.

These identities describe what actually ran; they are not yet the repository's
locked environment. Pinning is deferred until the corrected flow passes, so a
bad integration is not frozen merely because its layout stage succeeded.

## Setup limitations

Docker Desktop now works on the Windows host. Native Windows `make`, Icarus and
Yosys remain absent by design; the verified container workbench provides the
supported local lane. GitHub CI has not yet been moved onto that same lock, the
second Verilator simulation and M0 formal harness are not yet wired in, and the
official physical workflow still requires passing and clean pinned reruns.
