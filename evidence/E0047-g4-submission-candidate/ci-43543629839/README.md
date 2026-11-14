# G4 independent production reproduction

[Run 43543629839](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43543629839)
uses source `45c55f7cd95db2a883b0ffb5e864decd62d53601`. GDS, all ten official prechecks and
the eighteen-group actual public-netlist selection pass. The complete audit is
`PASS_ALL_SRAM_OFFICIAL_PHYSICAL_GATES`. This is the separately registered
reproduction run, not a retry replacing another physical outcome.

Six original ZIPs retain 1,729 members. Every archive
matches its GitHub API size/digest, and producing/consuming logs bind the actual
jobs to the submitted layout and netlist. The frozen audit includes
84 producing files; all match canonical Git blobs at the
recorded source. `storage.json` records unchanged archive storage and
`zip-files.json` covers every member. Optional rendering is outside these six
required verification archives.

All twenty production inputs match the adopted SRAM profile. The flow audit
checks 85 configured entries, 77
executed top-level stages, 2 nested stages and
8 gated skips, including their exact sequences and configuration
and state artifacts. Original Magic DRC, LVS and the required timing/electrical,
power-grid and antenna gates pass.

Worst setup slack is **5.5958856909900625 ns** and hold slack is
**0.12079138031701087 ns** at the 20 ns target. These are routed
measurements, not measured maximum frequency or silicon. The fast model mixes
-40 C standard cells and -55 C SRAM. The exact Magic contact alignment and SRAM
power/buffer/pin integration remain explicit.

The public tests reproduce 1,052 SPI, 1,160 I2C, four boundary and 36 abort
records. Seven UART groups execute their assertions; 97 RX/service landmarks
are retained, not complete UART TX traces. Netlist testing is functional
zero-delay simulation. `uart-landmarks.json` records that comparison scope.

Windows and isolated Linux CI replay the complete audit successfully and
reproduce the same result. Windows runs locally; [Linux run 43554467650](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43554467650)
uses execution source `7b73d99fbf300c1041aa930409ea63fc031d20f4`, distinct from the
physical source above. Its actual public alpha.7 workbench manifest is
`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307`;
its inspected configuration is `sha256:6f45e71162641466c4e9e08601a383c8a081c06b263114903a181d5f8f971451`.

Linux also rejects all nine deliberate evidence faults: pending workflow,
wrong archive digest, altered supply-port count, skipped public test, changed
submitted netlist, wrong job source, changed production identity, changed stage
configuration and changed stage-skip record. Rehashed semantic faults are
rejected beyond archive integrity. `controls-result.json` and the nine
`controls-logs/` files retain the actual failures.

`replay-runtime.json` binds the local Windows receipt and actual Linux CI
receipt, logs, verification reports and immutable image identities.
`linux-ci-binding.json` maps the unchanged copied CI member bytes to the
[common original proof](../linux-ci-43554467650/README.md), including its
33-member artifact, source, API and job-log records. The `verification.json`
member is named `verification-linux.json` here; its bytes are unchanged.

`startup-diagnostics/` preserves the earlier local Docker create-API EOF
failure (exit125), both bounded probe timeouts and the pending snapshot.
No verification or fault controls ran in that local attempt. The isolated CI
success makes no claim that local Docker recovered. `windows-runtime.json`
preserves the earlier Windows-only checkpoint; `replay-runtime.json` records
the completed comparison. Historical failure records remain unchanged.

Replay into fresh directories under `build/`:

```sh
python evidence/E0047-g4-submission-candidate/ci-43543629839/verify.py --output build/reproduction-replay
python evidence/E0047-g4-submission-candidate/ci-43543629839/verify.py --output build/reproduction-replay-controls --controls
```

Replays audit retained evidence and frozen source; they do not rerun place-and-route
or simulation. `SHA256SUMS` seals all retained files. Cross-run geometry comparison,
publication and submission readiness are separate G4 records. FPGA, analog,
fabricated-chip and owner-fluency completion are not inferred.
