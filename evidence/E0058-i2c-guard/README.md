# E0058 — I²C firmware timing guard on RTL and the submitted netlist

**At 50 MHz the 108-word candidate moved the controller's SDA transitions from 20–40 ns after falling SCL to 500–520 ns in the original transaction. All 172 paired requests retained identical SCL edge times, START/repeated START/STOP times and HALT times.** The released 96-word image remains the reference for a physical comparison. A larger command gap is a digital result. Its effect on voltage-crossing order depends on the receiver and the load. [Decision and expected outcomes](../../docs/decisions/0060-qualify-i2c-guard-and-measure-handoffs.md) · [NXP receiver timing and thresholds](https://www.nxp.com/docs/en/user-guide/UM10204.pdf)

| Per backend | Released (96 words) | 24-clock guard (108 words) |
| --- | ---: | ---: |
| Successful transfers reaching HALT | 93 | 93 |
| Requested NACKs at write address, data, or read address | 3 | 3 |
| First late stretch response or perpetual hold, once at each of 38 releases | 76 | 76 |
| Occupied bytes checked on every launch | 384 | 432 |
| Powered load-plan clocks per launch | 802 | 902 |
| Unstretched start of observation to HALT | 402.92 µs | 402.92 µs |

The 93 successes comprise the original transaction, two accepted near-deadline stretches on each of 38 releases, and sixteen extra address/payload combinations. The latter use addresses `08`, `2E`, `52`, `77` and write bytes `00`, `FF`, `55`, `AA` paired with their bitwise complements as replies. Each timeout reached HALT 40 ns after the 1 ms deadline. Both controller outputs were then released. The contract permits 320 ns. A target deliberately holding SCL low may continue to hold the physical line after the controller releases it.

Three further cases tested the timing oracle per backend. An 8-clock guard gave 180–200 ns and a 170-clock guard gave 3,420–3,440 ns. At 171 clocks the worst change was 3,460 ns, beyond the 3,450 ns data-valid limit. The oracle rejected the waveform even though the controller committed the correct `01` byte. All five unstretched cases kept the same SCL and boundary timing. The 24-clock candidate occupies twelve more instruction words and leaves twenty free.

Icarus RTL, Verilator RTL and Icarus on the archived G4 functional netlist executed 347 cases each. The three case journals and compressed pin archives matched byte for byte. The archive therefore retains one copy, bound by the separate execution receipts. Each backend matched the G4 released trace and all 159 council reference hashes. The shared target model sets its reply delay to 3,450 ns and the public-pin grid is 5 ns. The gate run uses functional cells and SRAM. The loader, target, observer and oracle are shared across the three runs. These comparisons establish implementation agreement under those assumptions. [Measurements and hashes](manifest.json) · [Icarus RTL](icarus/result.json) · [Verilator RTL](verilator/result.json) · [Submitted netlist](netlist/result.json) · [Original timing study](../E0049-review-council/panel-b/results/retime.json)

## Failure history

The first two Icarus launches failed to import the test module before observing a case. Staging the top and test in the scratch directory fixed discovery. Early runs also mistakenly compared timeout cleanup to two 5 ns samples. The retained first failing trace shows eight 5 ns samples, equal to two 20 ns core clocks. The independent oracle accepted the trace. The corrected check scores the existing public deadline and compares the historical guard cleanup separately. Incomplete journals, logs and the original rejected trace are retained. [Attempts and counts](initial-attempts/attempts.json)

## Reproduce

The offline audit needs Python 3.11+ and both release tags. It checks the production files against those tags, opens the submitted G4 archive, assembles each image, re-scores all 347 public traces and checks the three simulator receipts.

```powershell
python -B evidence/E0058-i2c-guard/audit.py
```

To re-run all the simulations, use a new output directory on H: with the locked workbench. The public fetch reads three digest-pinned IHP model files. The three simulations can run independently with the same read-only source checkout.

```powershell
$repo = (Resolve-Path .).Path
$scratch = (New-Item -ItemType Directory -Path (Join-Path $repo ("build/i2c-replay-" + [guid]::NewGuid()))).FullName
$image = 'sha256:9e300db4db672314f6dc5394d19e4b7d5d72917588fa2a963ace1a8118391909'
$mounts = @('run','--rm','--mount',"type=bind,source=$repo,target=/workspace,readonly",
    '--mount',"type=bind,source=$scratch,target=/workspace/build",'--tmpfs','/tmp:exec','-w','/workspace',
    '-e','PYTHONDONTWRITEBYTECODE=1','-e','GIT_CONFIG_COUNT=1','-e','GIT_CONFIG_KEY_0=safe.directory',
    '-e','GIT_CONFIG_VALUE_0=/workspace')
docker @mounts $image python3 -B evidence/E0049-review-council/panel-c/fetch_pdk_models.py --out build/pdk-models
docker @mounts --network none $image python3 -B experiments/i2c/guard_run.py icarus build/icarus
docker @mounts --network none $image python3 -B experiments/i2c/guard_run.py verilator build/verilator
docker @mounts --network none $image python3 -B experiments/i2c/guard_run.py netlist build/netlist --pdk-models build/pdk-models
```

The versioned `traces.jsonl.gz` contains one `[name, observations]` pair per line. The normalized time origin is the first marker-enabled idle state. The separate `cases.jsonl.gz` includes image readback digest, steps, target stimulus, oracle errors, terminal marker and timing. The public bench inventory queried each named board and read the native I²C class on an idle RP2350B. [Board inventory](remote-access.json) · [Local equipment sources](../../docs/research/western-cape-bench.md)
