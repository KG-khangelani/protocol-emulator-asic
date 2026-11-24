# Panel B research records

This record covers the hardware, electrical and embedded reviews. The independent assessment preceded the other panels’ drafts. The board addendum and challenge record carry the ensuing questions, replies and revised recommendation. The original investigation used pre-council source `e90cca228490423a7fe7c4ae40f7e669200b4d0e`. The reproduction uses the same qualified D48 inputs and committed G4 archives.

## Findings and reproductions

| Record | Inputs and result |
|---|---|
| [Independent assessment](independent-review.md) · [ETR fixture](etr-fixture.md) · [Challenge and rebuttal](challenge-rebuttal.md) | Three disciplinary perspectives, the opposing arguments, named board routing, scope and proposed physical test. |
| [Retained path inspection](results/retained-paths.json) | Two complete G4 log/test archives and selected members hash-checked. Worst retained setup and hold paths cross the SRAM boundary. One ideal combined write/read had 20 ns between a falling SCL and falling SDA command. |
| [Selected launch](results/launch.json) · [Prior contract](contracts/launch-contract.md) | Fifteen released images and an additional WAIT-at-PC-zero witness. Checks included public byte/readback expectations, 64 run edges and three adverse controls. The two DUTs used the same RTL, simulator and digital SRAM. |
| [Guarded replay](results/guard.json) · [Prior contract](contracts/guard-contract.md) | Four fresh interacting digital Icarus transactions. Unguarded RTL matched the retained submitted-netlist trace. Two guard lengths passed. The long guard returned the correct byte with a data-valid violation. |
| [Duration and stretch replay](results/retime.json) · [159 case records](results/retime-cases.jsonl) · [Prior contract](contracts/retime-contract.md) | A 108-word program reproduced all 76 SCL transitions and the elapsed time of the retained unstretched case while delaying controller data. The four-way boundary sweep covered each of 38 clock releases. The 171-clock negative still failed data-valid. |
| [Pad Liberty extraction](results/pad-tables.json) | Three pinned IHP source blobs and 42 tabulated load/slew points per corner. The conditional arithmetic assumes monotone transitions and a 20 ns gap *at the pad enables*. Any differential delay before the enables falls outside this calculation. |
| [PIO electrical challenge and revised ranking](ranking-rebuttal.md) · [One-wire rise calculation](results/onewire-load.json) · [Model assumptions](contracts/onewire-load.md) | The matched VM/PIO digital traces use one decoder sample per write slot. A remote sensor's allowed sampling window, guaranteed-high levels and reset-rise detection give distinct cases for a comparative bench. |

All guarded and retimed executions used the historical macro loader and an ideal wired-AND bus in feedback. The exponential threshold examples are subsequent calculations on recorded drive times. The archived netlist supplied the original baseline reference. New guard executions used the production RTL only.

## Replay from the checkout

On Windows PowerShell 7, use the pinned Docker Desktop workbench and a fresh H: directory. Build the project image with `tools/workbench.ps1 Build` if it is absent. From this record’s directory run the following command. The destination must be a new directory so previous evidence survives a retry.

```powershell
.\replay.ps1 -ScratchRoot H:\asic-council-rerun\panel-b-01
```

The runner mounts the checkout and these sources read-only, disables container networking and directs simulation products and temporary files to H:. It checks the G4 archives, compiles the public testbench and verifies the original public expectations, all case hashes, measurements and the adverse outcomes. The recorded full replay used a clean result directory with the existing checkout; all simulation and authoritative evidence inputs were unchanged from the research baseline. The checkout contained unrelated untracked files. Each tool ran in its own container. A separate fresh clone was unnecessary to this bounded reproduction and was not part of it.

With local installations of the same Linux toolchain, the equivalent working directory is the checkout root. Set `COUNCIL_SOURCES` to this record’s sources directory, `COUNCIL_REFERENCE` to its results directory, and `COUNCIL_RUN` to a fresh writable result directory on the experimental volume. Create the run directory before using the commands below. The three named subdirectories must initially be absent.

```sh
python3 "$COUNCIL_SOURCES/inspect_retained.py" > "$COUNCIL_RUN/retained-paths.json"
python3 "$COUNCIL_SOURCES/run_launch.py" --root . --out "$COUNCIL_RUN/launch"
python3 "$COUNCIL_SOURCES/guard_screen.py" --root . --out "$COUNCIL_RUN/guard"
python3 "$COUNCIL_SOURCES/retime_screen.py" --root . --out "$COUNCIL_RUN/retime"
python3 "$COUNCIL_SOURCES/verify_replay.py" "$COUNCIL_REFERENCE" "$COUNCIL_RUN"
```

Run `python -B sources/pad_tables.py` separately from this record’s directory to check the public Liberty sources over HTTPS. An offline copy of the three immutable files can be supplied with `--offline DIRECTORY`. The script validates their Git blob hashes before using the numerical tables. Its output matches the retained JSON after parsing.

Run `python -B sources/onewire_load.py` from the same directory to reproduce the numerical comparison with the DS18B20 and RP2040 input tables. It uses only Python's standard library.

The local image was `sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909`, Icarus/vvp was 14.0 development build `s20260301-328-geda9fdcd1-dirty`, cocotb was 2.0.1 and seed 20261124. The locked doctor reported Python 3.11.16 on its CLI; the cocotb embedded runtime identified its interpreter as 3.11.9. The unchanged production profile and SRAM model hashes accompany the results. [Doctor receipt](results/doctor.log) · [Portable replay receipt](results/portable-replay.json)

## First failures and controls

The first launch bench initialized reset low in its declaration. Icarus never delivered the intended reset transition at initialization and failed the very first public-direction expectation. The corrected bench drives reset low after simulation begins, then passes the positive checks and rejects the insufficient-idle, invalidating-register and transient-read controls. [First failure](firstrun/launch-failed.json) · [Rejected testbench](firstrun/launch-time-zero.sv)

The first guard invocation compiled the RTL but cocotb failed to discover a test module outside its working directory. No transaction ran. The correction staged the test module, Makefile and testbench in the private experiment directory. An attempted compile reuse still led recursive Make to compile a second time; the original one-compile budget was exceeded by one small compile. A subsequent fresh-directory rerun used the standalone runner with explicit private build and no reuse option. The script difference only changes its supervisor. The four images, traces, numerical results and expected negative matched. [Discovery failure](firstrun/guard-discovery.log.gz) · [First positive run and adverse control](firstrun/guard-pass.json) · [Exact historical supervisor difference](firstrun/guard-supervisor.patch)

The independent review also records the unavailable native `make` and the initial read-only Docker temporary-directory failures. The digital experiments used the existing workbench image. The physical investigation used the project's pinned LibreLane image and PDK. Live board measurements and fabricated-chip timing remain open. [Primary source identities](source-identities.md)

## Physical signoff rebuttal

The [signoff rebuttal](signoff-rebuttal.md) covers the real G4 fast SRAM hold and slow SRAM setup paths, the D46/D47 rules, layout readback, power, and the eight physical synchronizer paths. [The frozen conditions](contracts/signoff-scope.md) distinguish the initial archive inspection, later native geometry remeasurement, and fresh constrained STA. The retained native readback rejects a removed GDS pin shape, exchanged supply labels, a 15 nm hypothetical SRAM enclosure rule and an additional 125 ps clock uncertainty. The original D46/D47 failures remain in E0043. [Archive readback](results/signoff-audit.json) · [GDS remeasurement](results/contact-audit.json) · [Fresh hold sensitivity](results/sta-sensitivity.json) · [Fresh synchronizer transfers](results/sta-sync.json)

From a checkout with the project’s existing physical container and its pinned PDK staged as a Docker volume, run the following command in this record's directory. PowerShell 7, Docker and Python 3.11 or later are required. Use a fresh directory on H:. Optional `-PdkVolume NAME` selects the installed volume holding the original `ciel/ihp-sg13/versions/89d42ee6d2fd9b50b86a1aada6fee6673c3e6008` tree. The script runs all four independent audit programs with the repository and PDK mounted read-only and compares all JSON fields.

```powershell
.\replay-physical.ps1 -ScratchRoot H:\temp\protocol-council-physical-replay
```

For an offline standard-library-only inspection, run `python -B <record-directory>/sources/signoff_audit.py` from the checkout root. The remaining three physical scripts use the specified native image. KLayout loads the decompressed submitted GDS into anonymous process memory.
