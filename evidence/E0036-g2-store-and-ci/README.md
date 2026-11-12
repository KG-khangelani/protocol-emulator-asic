# E0036 - G2 current-revision audit and remaining qualification gates

Checkpoint 2026-11-12. **The clean G2 CI audit passes. The program-store
proof and physical qualification remain open. Production is unchanged.**

GitHub [run43213815994](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43213815994)
at `31ebf8247fab05f2e6e23bc94e1d861562f0f1b5` passes all three original G2 gates.
The independently downloaded archives match GitHub's SHA-256 digests.
[Verification](ci/verification.json) checks the exact candidate source files
against E0035's current manifest, protocol inputs against their committed Git
blobs, results, both simulators' records and the existing compact10 SPI reference.

- Both od128 and literal255 pass the **full** I2C matrix in Icarus and Verilator:
  1,160 identical records each, comprising 996 OK, six NACK, 152 bounded timeout
  outcomes and six rejected controls. This closes E0035's missing full literal
  second-simulator run without rewriting that earlier failed launch.
- Both candidates pass the real-store/instruction boundaries and scoped
  instruction proofs; generic complete-chip cost is unchanged.
- od128 passes 36 abort/reload records and the twelve legacy public groups
  in both simulators. All 1,052 SPI records equal the retained compact10
  expectations, including four expected input-hold failures.

The archives are identified in [artifact metadata](ci/artifacts.json).
Curated execution logs, result summaries, JUnit files and all public records
are retained here. `witnesses.tar.gz` archives preserve all 1,748 original
JSON witnesses byte for byte, with deterministic archive timestamps.
They are simulator/oracle observations, not physical measurements.

After downloading the three original ZIPs to `build/g2-ci-31ebf82/` and
extracting each into a directory named by its artifact ID, run
`python evidence/E0036-g2-store-and-ci/ci/verify_ci.py` to reproduce the audit.
The verifier reads protocol input bytes from the immutable source commit;
later workspace changes cannot silently substitute new inputs.

The [frozen physical qualification](../../docs/specs/g2-cmos5l-qualification.md)
uses a separate manual `gds-g2` workflow and the unchanged G1 physical lock.
Its new acceptance checker rejects missing/skipped groups, missing or changed
records, false netlist labels and mismatched submitted/tested bytes. Eight
checker test groups pass. Local non-staging preparation regenerates the exact
E0035 od128 hashes. The exact eighteen-group simulation selection still needs
a completed run; the first local attempt was interrupted by Docker's
`unexpected EOF` at 12:26:17 UTC, before a final result. A fresh CI gate is
provided for that selection. No G2 physical run is claimed at this checkpoint.

Additional memory-proof experiments are in progress. Initial whole-memory
approaches remain inconclusive; smaller groups have produced partial
unbounded passes. Completion requires every allocated word's transition and
read relation, the common control rules, reachability and checked negative
controls. Partial groups do not close the gate. The oversized direct-SAT
attempt was interrupted with the same Docker connection error; the cause
was not established. G2 remains active through its physical, integration and
publication gates, with G1 and owner-fluency boundaries preserved.
