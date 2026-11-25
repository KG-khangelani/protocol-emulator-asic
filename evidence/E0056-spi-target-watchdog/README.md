# SPI target with abort recovery and a selected-clock watchdog

**One 126-word program meets both recovery deadlines on the released digital design.** Across all 384 original abort/reselect cases the target released MISO in 61–99 ns, accepted the opposite command after the 160 ns handoff and returned its full byte. When CS stayed low and the clock stopped, all 32 response stalls reached a released timeout in 1,383–1,493 ns against a 2,000 ns limit. This closes the firmware objective that the 59- and 120-word programs left open. [Predeclared D58 criteria](../../docs/decisions/0058-combine-spi-abort-and-watchdog.md) · [Earlier VM and PIO comparison](../E0055-spi-target-comparison/README.md)

## Workload and measurements

An independent mode-0 requester owns SCK, MOSI and active-low CS. It sends A4 or A5, then clocks out 3C or A7 respectively, MSB first. A new selection occurs 160 ns after abort and the first rising SCK follows 300 ns later. During each command the target must leave MISO released. The observer records output enable as well as resolved data, so a driven zero and a released line remain distinguishable under the testbench's weak low bias. All pins, opposite-command reselection, invalid opcodes and four named faults come from the frozen E0055 fixture. [Requester and scorer](../../experiments/spi_target/requester.py) · [Public-port testbench](../../experiments/spi_target/target_tb.sv) · [Original 736 schedules](../E0055-spi-target-comparison/cases.json.gz)

| Original cases | Observed with the 126-word image |
| --- | --- |
| 28 ordinary and uneven transfers | 28 complete replies. Minimum setup 111 ns and hold 311 ns, against 60 and 40 ns required. MISO released 61–79 ns after the final falling edge. |
| 254 invalid command values | Every first mismatched prefix bit produced the error by the deadline, with MISO released. |
| 384 aborts followed by the opposite command | All released within 61–99 ns. The fresh command stayed quiet and every new response passed all eight bit samples and timing checks. |
| 32 aborts with CS held high | All released in 63–93 ns. |
| 32 missing-response-clock cases with CS held low | All reached a stable timeout with MISO released in 1,383–1,493 ns. The smallest observed margin to the timeout deadline was 507 ns. |
| Two stuck-select cases and four named faults | Both stuck selections, missing and late command clocks, an early deselection and a missing response clock produced the required terminal outcomes. |

The additional 1,952 schedules exercise the limits of this result. The 640 varied transfers use all 20 integer-nanosecond start phases of the 50 MHz core, randomized dummy data and independently chosen low and high intervals from 250 to 1,000 ns. All returned the fresh reply, with abort release in 60–99 ns. The 960 early and late aborts begin 1, 19, 41, 65, 99, 139, 199 or 241 ns after a clock transition. When CS rises just after a falling edge, either the preceding or the upcoming data bit can still be driven. The added scorer times the actual active branch until output disable and checks that it stays released through the handoff. The original fresh-frame checks still apply. The first interval before MISO ever drives has no active branch to measure and is excluded from this 960-case sweep. [Stress definitions and judging rules](../../experiments/spi_target/watchdog/stress.py) · [Exact additional schedules](stress-cases.json.gz) · [Measurements by variant, suite and simulator](measurements.json)

Across the 960 edge-adjacent aborts the smallest setup and hold measurements at a scored sample were 111 ns and 63 ns. The 352 remaining schedules stretch one low or high response interval at each of the 32 command/bit/polarity positions. At 1,000, 1,200 and 1,280 ns all 32 positions completed. At 1,320 ns 22 completed and 10 timed out. At 1,360 ns six completed and 26 timed out. At 1,400, 1,440, 1,480, 1,600, 2,000 and 3,000 ns all 32 timed out. Both completion and a clean bounded timeout are acceptable between the longest specified 1,000 ns half-cycle and the 2 µs timeout deadline. The mixed outcomes locate a position-dependent boundary at the tested phase. [Boundary scoring and raw-trace index](runs.json)

## How the two checks fit

The released VM polls CS and SCK in a two-instruction loop with a hardware iteration count of 32. With CS held low and SCK stationary the body takes 64 core periods, or 1,280 ns. Synchronization, entry, timeout dispatch and terminal reporting account for the rest of the observed interval. When SCK advances the program leaves the loop. When CS rises it returns to an entry that releases MISO and arms for a fresh command. Ordinary completion, invalid commands and selected-clock timeouts reach a terminal HALT. Aborted transactions can take the fresh command without a host operation. [Selected assembly](../../experiments/spi_target/watchdog/target.asm) · [Released instruction semantics](../../docs/isa.md)

Nine pairs of polling loops implement the 16 bit positions across the two replies. Several positions require the same next actions. At three branch points the program distinguishes paths by reading the bit it already drives on MISO through the production input synchronizer. The same six pins serve both implementations. The two marker pins report only the terminal result, starting on the instruction immediately before HALT. Three local copies of the timeout handler keep forward skips within the instruction's reach. The loader reads back all 504 program bytes and both payload registers in a 1,050-clock plan. The reply bytes are literals in this program, so changing a payload register alone cannot change the reply. [Program image](program.bin) · [Cold-load receipts and simulator versions](runs.json)

Native Windows assembly reproduced the binary used in the Linux simulations. The release assembler reports 24 backward-branch warnings on the selected source. A sequence of aborts can repeatedly jump back to the command entry. The watchdog bounds a selected clock stall, while total execution time also depends on the requester's behavior. [Full assembler diagnostics](manifest.json)

| Candidate | Resident size | Original 384 reselections | Original 32 selected stalls | Widest observed release on the 960 early/late aborts, Icarus RTL |
| --- | ---: | ---: | ---: | ---: |
| E0055 cooperative polling | 120 words | 384 passed | 0 passed | Outside the E0055 matrix |
| First counted-loop program | 123 words | 384 passed | 32 passed, latest 1,473 ns | 160 ns |
| Selected program | 126 words | 384 passed | 32 passed, latest 1,493 ns | 140 ns |

The first program used the entire abort budget on `edge-a4-6-0-19-1` and `edge-a5-1-0-19-1`. Before changing the image, D58 set a 140 ns selection threshold and kept every earlier check. Testing CS immediately before each of the three MISO decisions lowered the observed maximum by one 20 ns core period. It cost three words and increased the longest selected stall by 20 ns. Two of the 128 instruction slots remain available. The selected 504-byte image has SHA-256 `e5d25fc51d17684ede5615ece99501084c69380091c61c9ea58aba65b23c9e58`. [123-word comparison image](initial.bin) · [Immutable source revisions and content hashes](manifest.json)

## Cross-checks and scope

The 123-word comparison also passed all 2,688 original and extra schedules on the submitted netlist. Its 736 original traces matched Icarus RTL. Seven exact-edge abort traces differed on the extra sweep. The netlist's largest release was 158 ns there, compared with 160 ns on RTL. The decision to spend three more words uses the least margin observed on either representation. [Paired results](measurements.json) · [Differing trials](manifest.json)

The audit also checks the two recovery gates directly from intervals of constant port state, independently of the original scorer. It checks continuous release through the fresh command, verifies the required driven bit throughout each 60 ns setup and 40 ns hold window, and measures the stable timeout terminal. It accepts both counted-loop images and rejects the historical 59-word image on its first missed handoff and the 120-word image on its first selected pause. [Interval checker](audit.py) · [Historical traces and outcomes](../E0055-spi-target-comparison/README.md)

On all 736 original cases, Icarus RTL, Verilator RTL and the submitted functional netlist produced identical timed port traces. On the 1,952 extra cases the netlist matched Verilator on every trace. Icarus RTL agreed on 1,943. In the other nine, CS deasserted exactly on a rising core edge, 1 ns after SCK fell. Every backend met the release deadline and completed the next command. One Icarus RTL trace also showed a change of the driven bit before release. The largest release on the 960-case edge sweep was 138 ns for the netlist and Verilator, and 140 ns for Icarus RTL. [Per-run measurements](measurements.json) · [Cases with different traces](manifest.json)

A follow-up moved that same requester by −2, 0 or +2 ns over both commands and all seven applicable falling-edge bit positions, preserving dummy data and relative spacing. All 42 trials passed in Icarus RTL, Verilator RTL and the submitted gate netlist. All three returned identical traces in the 28 displaced cases. For the 14 exact coincidences Verilator and the gate netlist agreed, while Icarus RTL differed on nine. The largest release interval in the 42 trials was 140 ns. This locates a simulator scheduling dependency at the coincident edge. The physical synchronizer's setup/hold aperture remains unmeasured. [Diagnostic schedules](../../experiments/spi_target/watchdog/stress.py) · [Port trace index](runs.json)

The 14 exact coincidences repeat schedules in the 1,952-case sweep. Only the 28 shifted schedules are new. For example, during A5 reply bit 3, the −2 ns case released in 62 ns on all three models. At coincidence, Icarus RTL released in 140 ns and the other two in 60 ns. At +2 ns all three released in 78 ns. The timing budget uses the larger observed value.

Six deliberately defective firmware images ran through the same loader and Icarus RTL. Extending the response watchdog left MISO driven after the deadline. Shortening it lost a legal slow reply. Halting on abort lost the fresh byte. Reversing a MISO branch returned wrong data. Releasing a required zero failed the drive-and-data check. Driving a marker before the terminal failed the marker check. Each image and its actual pins can be rescored. [Mutations](../../experiments/spi_target/watchdog/controls.py) · [Observed rejections](controls.json.gz)

The varied requester used 235 distinct fresh-command dummy bytes, including 00 and FF. Disassembly of the reply section finds pin reads only on SCK, CS and MISO. The three reads of MISO observe the target's driven bit. This explains the observed independence from dummy MOSI and spare-pin bias. [Binary structure check](audit.py)

The 160 ns handoff is a research deadline on an ideal 50 MHz digital clock. The two-register input synchronizer and the digital readback of a driven MISO are part of the simulation. Pad turnoff, bus capacitance, receiver thresholds, contention and metastability need physical measurements. A named requester's handoff deadline and a characterized target-branch fixture would determine whether the observed 20 ns digital headroom is sufficient. The separate calibrated UART handoff measurement also remains open. [Original workload contract](../E0049-review-council/panel-c/spi-target/spi-target-contract.md) · [Receiver-end measurement procedure](../E0049-review-council/panel-b/fixture/bench.md)

## Reproduction

Two gate-netlist launches repeatedly read the same 15 MB compiled model across the Docker host mount. Their replacements use the same cold-load plan, submitted Verilog and release assembler, and keep an immutable copy of the compiled model in RAM. The first launches were stopped after issuing 439 and 333 schedules respectively. Only completed simulations enter the tables. The first repository check also reached its five-minute timeout during concurrent simulations after eight unit-test groups completed. [Superseded launches and matching input hashes](superseded.json) · [Timeout receipt](check-timeout.json) · [Partial check log](check-timeout.log.gz)

From a checkout with the two stable tags and experiment commits, reassemble the image and rescore the retained pins with Python 3. The audit rebuilds both programs, checks the compile-time polling structure, verifies the frozen requester schedules, checks the six adverse runs and compares the twenty qualified physical inputs with both stable tags. Each pin row records elapsed nanoseconds, output-enable bits, resolved MISO, terminal marker and HALT indication. [Audit](audit.py) · [Execution receipts and pin-file paths](runs.json)

```powershell
python -B tools/assembler.py experiments/spi_target/watchdog/target.asm --out build/spi-watchdog-image
python -B evidence/E0056-spi-target-watchdog/audit.py
```

To execute the design again from an H: checkout, each command below uses Docker Desktop and creates a fresh directory under `build/`. The default image is the digest used for the recorded runs. On a different machine, `-Image` accepts a local build or the [published workbench digest](../../docs/submission.md). For a gate run the script fetches three hash-checked functional libraries. An available model directory can be passed with `-Pdk`. All simulator runs disable networking and compare their output with the corresponding retained pins. [Replay script](../../experiments/spi_target/watchdog/replay.ps1) · [Doctor](doctor.log.gz) · [Repository check](check.log.gz)

```powershell
.\experiments\spi_target\watchdog\replay.ps1
.\experiments\spi_target\watchdog\replay.ps1 -Backend gate -Suite stress
.\experiments\spi_target\watchdog\replay.ps1 -Backend verilator -Suite ties
.\experiments\spi_target\watchdog\replay.ps1 -Backend controls
```

Fresh runs through that PowerShell entry point reproduced the 736 original RTL traces, all 42 phase-neighbor netlist traces and all six rejected controls byte for byte. The isolated retry of `make check` passed all 163 tests in 16 groups. The E0055 audit also passed against its original records. The thirteen primary execution receipts include UTC start and end times. [Fresh replay and check receipt](clean-replay.json) · [Primary runs](runs.json)
