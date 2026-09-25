# E0011 — Node 24 fast-CI action qualification

GitHub run [36124783158](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36124783158)
tested commit `4e00a0c6da1f8e80b0b1a372af4bd457234379c4` on 25 September
2026. The locked fast-verification lane passed after its two Docker orchestration
actions moved from Node 20 releases to immutable Node 24 release commits.

## Why this change existed

The preceding clean run passed but GitHub warned that the pinned setup-buildx
and build-push actions declared Node 20. GitHub was applying a compatibility
override and running them on Node 24. That meant the effective runtime no longer
matched the runtime declared by the pinned source.

An action is setup code executed by GitHub around the job. The EDA tools still
live inside the separately locked Docker image. Updating these two actions did
not change Icarus, Verilator, Verible, Yosys, SBY, Z3, Python, cocotb, the RTL,
or the physical-flow snapshot—but clean requalification was still required.

## What passed

| Gate | Result |
|---|---|
| Immutable setup-buildx v4.4.1 manifest declares Node 24 | PASS |
| Immutable build-push v7.4.0 manifest declares Node 24 | PASS |
| Both release commits reported verified by GitHub | PASS |
| Locked workbench built and retained the qualified image identity | PASS |
| Doctor, static, lint, Icarus, Verilator, formal, and generic synthesis | 7/7 PASS |
| Reproducibility evidence collection and artifact upload | PASS |
| GitHub check annotations after the run | 0 |

Both RTL simulators again passed two tests. The formal proof and cover passed,
the deliberately broken increment-by-two mutant was rejected as expected, and
generic synthesis passed. The built image ID is byte-for-byte the same identity
recorded by E0007: `sha256:1b756a6b8cbfd5536aa7b85c13acf7aa4a293dc42973129721dd8aa19d66e05b`.

`action-manifests.json` records the exact release commits, action-manifest blob
IDs, SHA-256 values, declared runtimes, and GitHub verification observations.
`manifest.json` is the clean CI evidence manifest. The two JUnit files and image
inspection record are retained here; `annotations.json` preserves the empty
annotation response.

## Claim boundary

This qualifies the Node 24 action pins for this GitHub-hosted fast-CI lane. It
does not claim compatibility with an older self-hosted Actions runner, change
the EDA tool qualification, add protocol functionality, or provide physical or
silicon evidence. The official CMOS5L result remains E0010.

The complete downloaded verification artifact remains under ignored
`build/artifacts/E0011-node24-fast-ci-36124783158/`. GitHub reports that the
original artifacts expire on 24 December 2026.
