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
failed JUnit results. `Formal` proves the M0 state/output contract, creates a
reset-to-wrap witness, and confirms the assertions reject an increment-by-two
mutant. `Synth` runs generic Yosys and leaves `build/synthesis.log` and
`build/synth.json`. `Evidence` records source hashes, exact commands, versions,
and stage status. See `formal/README.md` for the proof assumptions and limits.

GitHub's Docker setup and build actions are also pinned by commit. E0011
qualifies Node 24-native setup-buildx v4.4.1 and build-push v7.4.0: the locked
image identity is unchanged, all seven stages pass, the artifact uploads, and
the prior Node 20 deprecation annotation is absent. These actions orchestrate
the container; they do not replace or redefine the EDA tools inside it.

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

### Qualified physical-flow snapshot

E0003 first resolved the CMOS5L action branch to action commit
`3412659307918422f3f0727917cf9b499aaca588`, Tiny Tapeout support tools
`d66cf179e7bc4d296362ab7e2e3b344dc3c4f665`, LibreLane `3.1.0.dev3`, and
IHP Open PDK `2bbec755dc67ca3db0261c3d6163e15735d66710`. The GDS and precheck jobs
passed. The gate-level runner used Python 3.11.16 and Icarus 13.0, but failed
at elaboration because `test/Makefile` omitted `sg13cmos5l_udp.v`. That source
list is corrected, and E0006 passes GDS, gate-level regression, and all nine
prechecks with the same candidate identities. Direct workflow actions and the
support-tools/LibreLane inputs are now pinned. Clean run E0010 passes the same
three gates, reproduces E0006's metrics, and has identical non-timestamp GDS
records. This snapshot is qualified for M0. The official composite action
remains a recorded transitive trust boundary.

## Setup limitations

Docker Desktop now works on the Windows host. Native Windows `make`, Icarus and
Yosys remain absent by design; the verified container workbench provides the
supported local lane. E0007 proves the same image recipe, two simulators, formal
verification, and synthesis in clean GitHub CI. E0009 proves the complete fast
ladder from a fresh Windows clone. E0010 archives the clean repository-pinned
physical result. The optional FPGA and devcontainer lanes remain unverified.
