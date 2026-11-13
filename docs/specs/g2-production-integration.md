# G2 production integration gates

Predeclared 2026-11-12 while the separate D38 and D39 physical trials run.
Production RTL remains unchanged until a chosen candidate passes the fresh
pinned physical, precheck and real-netlist gates.

An isolated checkout of 426cea1 with only E0038's five RTL files substituted
ran the unchanged default Icarus suite: 18 of 22 groups passed, four failed.
The complete D39 eighteen-group public suite separately passes both simulators.
The integration probe identifies old harness assumptions; it is not a chip
qualification, and its failures must not be relabelled as passes.

| Default test | Assumption exposed by the probe | Current contract to preserve |
| --- | --- | --- |
| invalid_length_never_releases_engine | Length nine is invalid for the original eight-word store | D39 accepts lengths 1..128; invalid length commits still clear ready |
| loop_target_overflow_faults_without_alias | PC32 overflows a five-bit counter immediately | Eight-bit PC32 is representable, then invalid fetch faults outside the committed image; no alias to word zero |
| shift_invalid_partial_and_reset_fail_closed | Manual SHIFT_STEP bit zero is reserved | D37 assigns bit zero to general open-drain output; genuinely reserved encodings and partial-byte consistency still fault |
| spi_mode0_abort_reload_and_capacity_boundary | A ten-word length cannot be committed | D39 has 128 real words; keep the abort/reload checks and use the applicable capacity boundary |

The old direct-engine harness also reports three width warnings: PC, loop
start and loop end are connected as five bits to eight-bit candidate ports.
The probe's exact JUnit, log, source/harness hashes and manifest are retained
under E0038/integration-probe. No production source was changed by the probe.

Required integration work:

1. Declare the current source/ISA/capacity profile and verify its exact source
   hashes. Keep historical tests/builders tied to their archived source and
   contract. A changed rejection domain is an explicit interface extension.
   Preserve D34's exact physical base in `experiments/physical/d34-config.json`;
   historical G1/G2 staging must copy that checked archive explicitly. Derive
   SRAM additions from the same input. Do not make historical generation
   depend on the future production `src/config.json`. The production profile
   still needs its own qualified configuration, workflow and metadata checks.
2. Make normal test, formal, lint, synthesis and evidence commands evaluate the
   current production files. Require the complete public UART/SPI/I2C matrix,
   both simulators and source-matched formal evidence. Preserve all meaningful
   historical assertions on their proper baseline; do not silently discard
   failing groups or accept truncated direct-engine observations.
3. Version evidence labels and coverage rules where necessary. Distinguish
   public RTL, a directly driven core, a harness smoke test and actual CMOS5L
   netlist evidence. Require exact known test identities, outcomes, source
   hashes and retained public records. Keep UART service and SPI hold limits.
4. Reuse a completed verification result only after checking its exact inputs
   and artifact bytes. Avoid rerunning expensive complete matrices just to
   package evidence, and retain enough witnesses to inspect failures. Set
   explicit tool wall limits appropriate to the already measured full suite;
   these do not change protocol or physical acceptance thresholds.
5. Copy the qualified five RTL files into production only after final physical
   artifact audit. Bind the adoption decision to identical candidate/production
   source hashes, the combined regression and the actual physical workflow
   revision. Preserve failed candidates, G1 evidence and owner-fluency status.
6. Publish the qualified milestone with the current source, audited original
   physical archives, reproducible checks and matching workbench image. Verify
   downloaded release assets, image identity, public access and tag checks.

This document specifies integration acceptance, not a completed integration
or approval to label an unfinished physical run successful. G3's user-facing
assembler remains separately ordered.
