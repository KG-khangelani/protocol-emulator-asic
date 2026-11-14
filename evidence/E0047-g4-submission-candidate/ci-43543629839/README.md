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

Windows replays the complete audit successfully. `verification-windows.json`,
`invocation-windows.json`, `replay-windows.log.gz` and `windows-runtime.json`
retain the actual command, exit code, complete audit equality and log/hash
bindings. Linux replay and its nine deliberate corruption controls remain
pending in this record. The local Docker invocation exited125 with a create
API pipe EOF before any replay output directory was created; two bounded
minimal startup probes also timed out. `startup-diagnostics/` preserves those
receipts and the original pending snapshot. None is counted as a verification
pass. No Docker daemon or other service was restarted by this agent.

Replay into fresh directories under `build/`:

```sh
python evidence/E0047-g4-submission-candidate/ci-43543629839/verify.py --output build/reproduction-replay
python evidence/E0047-g4-submission-candidate/ci-43543629839/verify.py --output build/reproduction-replay-controls --controls
```

Replays audit retained evidence and frozen source; they do not rerun place-and-route
or simulation. `SHA256SUMS` seals all retained files. Cross-run geometry comparison,
publication and submission readiness are separate G4 records. FPGA, analog,
fabricated-chip and owner-fluency completion are not inferred.
