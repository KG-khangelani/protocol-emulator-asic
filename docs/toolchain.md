# Toolchain and reproduction

## Source baseline

Official template: `TinyTapeout/ttihp-verilog-template`, `cmos5l`, commit
`b86a2a781484bcab7ba522dc5de540086695a430`. See `upstream-template.json` for
the verified file inventory. `src/config.json` is preserved byte for byte.

The upstream devcontainer had `PDK=ihp-sg13g2` while its CMOS5L workflow and
test harness used `ihp-sg13cmos5l`. The devcontainer variable is aligned with
the latter. That edit still requires a container/physical build to validate.

## Fast local loop

`make setup` creates the Python environment. `make doctor` reports prerequisites.
`make check` performs static consistency only. `make test` invokes cocotb/Icarus
and rejects missing, empty, skipped or failed JUnit results. `make synth` runs
generic Yosys and leaves `build/synthesis.log` and `build/synth.json`.
`make evidence` records source hashes, exact commands, versions and stage status.

The Python dependency versions in `test/requirements.txt` are inherited from
the pinned template. Native compiler, OS and transitive dependency versions are
not fully locked yet; the evidence manifest records observed versions.

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

## Setup limitations

The setup runner lacks Icarus, cocotb, Yosys and Docker. Native installation
could not complete because the environment could not perform package-manager
privilege transitions; a Python package lookup also yielded no usable HDL tool.
These are environment observations, not a verdict on design correctness.
No physical-flow output, timing margin or successful simulator run was produced.
