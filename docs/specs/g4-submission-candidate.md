# G4 final candidate and submission-readiness contract

Frozen before execution on 2026-11-14 under D49, from G3 closure
`59dd1dc537d0ec405f320d564df4436bd3f9dd2a`. G4 ends at a reproducible,
documented submission candidate. Actual entry submission, hardware spending,
fabricated-chip results and the owner's learning assessment remain separate.

## Candidate and conditions

Use the unchanged D48-qualified `od128-sram` core: interface 0x22, 128 logical
32-bit words, one 256-by-32 SRAM macro and 353 register bits. E0047's freeze
record binds all twenty physical inputs, metadata, workflow and toolchain lock.
Preserve the G2 production profile as the original adoption record; a new
final-qualification record must not rewrite that history.

Keep the pinned 8x4 CMOS5L flow, 20 ns target, every acceptance limit, real
macro views and the complete 85-stage construction/check sequence. D43-D47's
power integration, input buffers, pin geometry, exact Magic contact alignment
and full-height power-port selection remain explicit. The original complete
rule check stays enabled. The fast model set combines -40 C standard cells
and -55 C SRAM; this is not an isothermal characterization.

No new RTL or instruction semantics are planned. Documentation corrections
cannot silently change hardware, program bytes or acceptance criteria. If a
material change is necessary, retain the failed gate, explain the change,
freeze a new candidate and repeat affected qualification.

## Physical qualification and reproduction

1. Commit this contract and the corrected datasheet, then dispatch the existing
   production `gds` workflow twice at the same immutable commit. Each run uses
   a separate clean Actions checkout and fresh physical output. Record both
   IDs before interpreting results. They are primary qualification and
   independent reproduction, not retries replacing unsuccessful evidence.
2. Each run must pass GDS, routed timing/electrical/antenna/DRC/LVS checks, all
   ten official prechecks and all eighteen actual-netlist public test groups.
   Require UART, four-mode/both-order SPI and I2C coverage, including 1,052 SPI,
   1,160 I2C, four boundary and 36 abort records. Missing/skipped gates fail.
3. Retain all six original archives per run. Audit API sizes/digests and the
   producing/consuming job logs, every member, source inputs, actual
   container/PDK identity, submitted netlist/GDS and semantic results. Freeze
   producing audit dependencies, run a pinned Linux replay and require
   meaningful corrupted/incomplete-evidence controls.
4. Compare both submitted netlists, source/macro identities, normalized GDS,
   stage results, timing/area and public observations. GDS comparison may
   exclude only BGNLIB/BGNSTR timestamps. Record exact geometry reproduction
   separately from independently passing acceptance; investigate unexpected
   differences and never relabel different geometry as identical. Compare G2
   as a separate continuity check, preserving its original measurements.

## Documentation and software

Provide readable architecture and exact current ISA guides, reset/enable and
host-interface instructions, examples, verification and an honest AI-use
account. Explain SRAM/prefetch and measured design decisions with original
evidence, including rejected P and register-store trials. Separate generic
counts, technology area, routed results and actual hardware observations.
State external host, bounded-service, input-hold, pull-up, level-shift,
voltage and reload requirements.

Correct the stale Tiny Tapeout datasheet and verification overview; preserve
old specifications as historical contracts. Retain G3's exact example words
and independent oracles. Final clean CI must run normal production commands
and the documented example entry point with invalid/wrong-program controls.
Check the actual standalone distribution and deterministic Windows/Linux
packaging. A larger compiler or hardware transport adapter is not implied.

## Release and submission packet

The intended stable tag is `v0.1.0`, after required gates pass. Include current
guides/examples, fresh original physical archives, source identities,
reproducibility records, known limits and checksums. The normal publisher
must test and publish the matching workbench image. Verify actual anonymous
downloads, archive members, source/version/image identity and all release-tag
jobs. State registry-check scope accurately: manifest/HEAD access is not a
full image pull.

Recheck official rules before closure and retain a dated mapping. Prepare the
public repository/release links and a concise write-up addressing published
requirements. The final form is unavailable at activation; record that status
without claiming an entry was sent. Reconcile changed requirements before
marking readiness.

All five G4 checks must map to evidence. G5 stays optional; G6's M0 teach-back
stays pending. Hardware/analog/FPGA results, unrestricted interoperability and
measured Fmax remain explicit nonclaims.
