# Research ledger

Question: **What is the smallest computational substrate that can efficiently
express useful digital communication protocols under hard temporal constraints?**

## Verified facts

| ID | Fact | Evidence |
|---|---|---|
| F1 | Competition requires an open-source reprogrammable protocol emulator, deadline 18 Jan 2027 | S1, `sources.md` |
| F2 | Current allocation is 6x4; 8x4 is only a possibility in the brief | S1 |
| F3 | CMOS5L source snapshot was imported with matching blob identities | `upstream-template.json`, initial Git commit |
| F4 | M0 can be placed and routed in the 6x4 CMOS5L allocation with positive reported slack at the 20 ns flow target and clean recorded physical checks | E0003, E0006, E0010 |
| F5 | The first official gate-level job cannot elaborate because its source list omits the PDK file defining `ihp_dff_r` | E0003 |
| F6 | The locked Linux/amd64 workbench passes exact-version checks, Verible lint, two M0 RTL tests and generic synthesis on Windows Docker Desktop | E0005 |
| F7 | The corrected official run passes GDS generation, both generated-netlist tests, and all nine Tiny Tapeout prechecks | E0006 |
| F8 | E0003 and E0006 have byte-identical GDS non-timestamp records; their full hashes differ only because 256 bytes in library/structure timestamp records changed | E0006 |
| F9 | The M0 public-pin transition/output assertions pass k-induction, the reset-to-wrap covers are reachable, and the same assertions reject an increment-by-two mutant locally and in clean remote CI | E0007, `../formal/README.md` |
| F10 | The read-only upstream canary remotely observes the live Tiny Tapeout CMOS5L action ref without altering qualified pins; its baseline state was CURRENT | E0008 |
| F11 | A fresh Windows clone passes the full locked fast ladder without native EDA commands on PATH, and its compared physical-input byte hashes equal Linux CI | E0009 |
| F12 | The clean repository-pinned physical flow passes GDS, both gate-level tests and all nine prechecks; it reproduces E0006's metrics and every non-timestamp GDS record | E0010 |

## Working hypotheses

| ID | Claim | Falsification gate | State |
|---|---|---|---|
| H1 | A temporal VM covers UART, SPI and I2C compactly | Requires protocol-specific RTL escape paths or misses timing/fit | Unproven |
| H2 | Explicit timing instructions simplify verification | Comparable controllers require fewer properties or expose fewer failure modes | Unproven |
| H3 | The candidate instruction set is near minimal | Removing/merging an instruction preserves coverage at acceptable cost | Unproven |
| H4 | Interpretation overhead fits useful bit timing | Measured execution/post-route timing misses required sample/edge windows | Unproven |

## Design decisions

| ID | Decision | Basis |
|---|---|---|
| D1 | Preserve official template; use an isolated GPIO M0 baseline | `decisions/0001-bootstrap.md` |
| D2 | Use 50 MHz as the initial test/flow target, not a supported-performance claim | Inherited 20 ns template constraint; reassess after hardening |
| D3 | Use a locked Docker workbench for the fast verification lane | `decisions/0003-locked-workbench.md` |
| D4 | Keep M0 physical acceptance on the official flow with direct actions and successful candidate inputs pinned immutably | `decisions/0004-pinned-physical-flow.md`, E0006, E0010 |

## Experimental results

| ID | Experiment | Result | Limit |
|---|---|---|---|
| E0001 | Bootstrap consistency and tool availability | Static pass; HDL stages blocked | No behavioral or physical evidence; `../evidence/E0001-bootstrap/` |
| E0002 | GitHub CI baseline | Static, RTL and generic synthesis PASS; docs PASS | No physical/GL proof; `../evidence/E0002-ci/` |
| E0003 | First official CMOS5L run | GDS and all prechecks PASS; gate-level compile FAIL | Not a complete M0 result; no functional GL run or clean rerun; `../evidence/E0003-cmos5l-first-run/` |
| E0005 | Locked local open EDA workbench | Doctor, static, lint, 2 RTL tests and generic synthesis PASS | Formal and physical fit NOT_EVALUATED; `../evidence/E0005-locked-workbench/` |
| E0006 | Corrected official CMOS5L run | GDS, 2 gate-level tests, and all 9 prechecks PASS | Mutable workflow ref at dispatch; no clean repository-pinned rerun; `../evidence/E0006-cmos5l-corrected-run/` |
| E0007 | Locked fast CI and M0 formal proof | Static, lint, 2 Icarus tests, 2 Verilator tests, formal proof/covers/mutant, and generic synthesis PASS | Written-property coverage only; no physical or silicon proof; `../evidence/E0007-locked-fast-ci/` |
| E0008 | Upstream drift canary baseline | Remote monitor PASS; live and qualified Tiny Tapeout action commits match | Timestamped observation only; no automatic upgrade or physical proof; `../evidence/E0008-upstream-canary/` |
| E0009 | Fresh Windows clone verification | Doctor, static, lint, both simulators, formal, and generic synthesis PASS; cross-platform input hashes match | Reused qualified local image; no physical proof; `../evidence/E0009-fresh-windows-clone/` |
| E0010 | Repository-pinned CMOS5L qualification | GDS, 2 gate-level tests, and all 9 prechecks PASS; E0006 metrics and non-timestamp GDS records reproduced | Target timing is not Fmax; functional gate simulation is not silicon evidence; `../evidence/E0010-pinned-cmos5l-run/` |

## Open questions

- Q1: What timing quantum and external-input latency meet useful protocol rates?
- Q2: What program-memory type/capacity fits after physical overhead?
- Q3: How are programs and payloads loaded/read back after fabrication?
- Q4: What electrical assumptions and synchronization delays govern each pin?
- Q5: Which stretch protocol demonstrates the most reusable capability per cost?

## Rejected approaches

None rejected by experiment yet. Protocol-specific fixed blocks are a useful
cost baseline but are not the intended reprogrammable competition solution.
Do not retrospectively label unexplored alternatives as experimentally rejected.
