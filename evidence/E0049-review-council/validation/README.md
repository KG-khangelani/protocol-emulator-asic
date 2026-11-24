# Production checks during the council

The project provides normal `make doctor`, `make check` and `make test` targets. The last target runs the full production Icarus regression, an RTL harness smoke test and a separate check that ties the two sets of results to their inputs. The public G4 submitted-netlist work uses a different entry point. [Production verification layers](../../../docs/verification.md) · [Submitted-netlist experiments](../powered-netlist/README.md)

## First run and the waveform failure

The 16:37 UTC Icarus run passed all thirty groups, including the existing SPI, I²C, bank-boundary and abort controls. In the subsequent smoke test Icarus' FST writer reported two failed `mmap` calls and the simulator terminated before generating JUnit. `/tmp` was then a Windows H: bind mount inside the Linux container. For the retry the chair supplied a native Linux memory-backed `/tmp`, disabled core dumps and kept the public RTL, test sources, test directory and durable outputs on the same H: paths. The smoke test passed and the unmodified production provenance checker accepted both stages. The first full `make test` invocation exited unsuccessfully. [Original failure output](first-fst-failure.log.gz) · [Failed stage receipt](first-fst-failure-receipt.json.gz) · [Recovered stage pair and source identities](first-recovered-provenance.json.gz)

The bounded rerun below starts in an unused H: directory. It mounts the checkout read-only, gives `build` an isolated H: directory and copies the 45 Git-tracked test files byte for byte before mounting that copy at `/workspace/test`. This protects any existing harness waveform in the checkout when the stock target unlinks and rewrites its output. Named evidence, compilation output and waveforms live under H:. The FST writer's temporary memory disappears when the container exits. The host used Docker Desktop, with its WSL data directory on H:, and the existing pinned local workbench image. [Exact environment and entry point](replay.ps1)

```powershell
.\evidence\E0049-review-council\validation\replay.ps1 -RunName fresh01
python -B evidence/E0049-review-council/audit.py
python -I -B evidence/E0049-review-council/validation/audit_controls.py
python -B tools/production_sram.py
```

The three audit controls keep the original evidence files untouched. Going from seventeen remote slot starts to sixteen while leaving the terminal marker intact failed the 1-Wire check. Restoring the nominal UART service limit to a +2% transmitter failed the service-bound check. Moving one public MISO release to 160 ns while retaining the late stopped-high observation in the other case failed the PIO check. Each produced the intended rejection. [Control definitions](audit_controls.py)
