# Verified G5 software publication

Observed 2026-11-15. [v0.1.1](https://github.com/KG-khangelani/protocol-emulator-asic/releases/tag/v0.1.1)
publishes source `022834146efcb5f388a4d6ec23b3b705a0df7ef8`.
`verification.json` records `PASS_G5_RELEASE_AND_PACKAGE` from actual isolated
Linux run [43702683490](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43702683490).
The original execution, frozen auditor and authenticated transport are in
[the companion CI record](../publication-ci-43702683490/README.md).

All 22 assets were downloaded anonymously and matched against GitHub's
digests, both checksum manifests, the original publisher artifact and the
four rebuilt G5 files. The downloaded 25-member bundle runs outside the
repository with isolated Python: both programs rebuild into eight identical
compiled files and all twelve independent checker tests pass. The downloaded
G5 CI ZIP is identical to the retained qualification original.

Publisher run [43698444537](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43698444537)
passes all eight normal-command stages, including both RTL simulators, formal
checks and synthesis. Its 7,715,770-byte original artifact `14156503337.zip`
contains 1,948 members and has SHA-256
`3f826e53800bba7c3346224a15af48b25c4c9923c3ce12dd8d777fe0a3fbfa9a`.
All 361 publisher inputs match the release Git blobs; the frozen semantic
parsers reproduce the stage summaries. Both repository-check executions pass
159 tests. All ten tag workflows and all 23 jobs pass.

The public workbench is
`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:977a4dc20fe558bb84d941b5aa572d5f456866660ea6a2c4f3a9badd87f7811e`.
Its manifest and configuration bodies are hashed, both version/source aliases
resolve to that manifest, and its source labels and configuration ID match
the actual image tested by the publisher. Anonymous HEAD requests verify
access and sizes for all thirteen layers. This audit does not claim a full
pull of the newly published image. The audit itself executes in the previously
verified G4 workbench; its distinct identity is recorded in the CI receipts.

`release.json`, tag records, `tag-workflows.json`, original job log and
`artifacts.json` preserve the API observations. `downloaded/` preserves the
actual public bytes, `downloaded-smoke/` the standalone execution, and the
registry JSON files the actual returned bodies. `retention.json` seals the
captured files; this explanatory README is added after that capture.

This is a software milestone on the unchanged twenty qualified physical
inputs. G4's v0.1.0 remains the hardware/layout reference. No new physical,
silicon, analog, Fmax, owner-fluency or competition-entry result is implied.
