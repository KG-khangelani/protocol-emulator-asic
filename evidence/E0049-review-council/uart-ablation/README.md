# What the timed byte instruction buys on UART

On the production SRAM RTL, the two-frame transmitter and receiver can use one counted loop of manual shifts per frame. Both preserve the checked pin levels, direction, raw-data lifetime and semantic HALT or FAULT edges. They cost more program memory, and the released receiver software rejects the manual program's successful result. [Prospective contract](contract.md) · [Result](result.json) · [Per-case observations and negative controls](case-observations.log.gz)

| Measured for each version | Released burst | Manual shift and wait |
| --- | ---: | ---: |
| Transmit program / public load edges | 8 words / 76 | 17 words / 152 |
| Receive program / public load edges | 8 words / 76 | 18 words / 160 |
| Good TX / RX terminal status, hex | A7 / A7 | B0 / B1 |
| First / second bad-stop status, hex | E6 / E6 | E8 / F0 |
| Missing-start status, hex | E1 | E1 |

Each version passed 272 transmitter and 278 receiver cases. The 1,100 cases together checked 666,060 runtime clocks, including the terminal clocks used to observe the host. At P=4 the screen covered all 256 complementary byte pairs and distributed four start phases across them. At P=434 it crossed four pairs with all four phases. Each receiver also faced one first bad stop, second bad stop and missing start per period. The missing-start probe extended the contract after panel A's challenge. Each case reset, loaded and read back the whole program through its standard chip-port plan. At each running edge the fixture checked the dedicated status, two dedicated register reads, GPIO drive data and direction. The TX peer held the returned data low, so RX supplies the evidence for distinguishing the two captured values. [Fixture](uart_tb.sv) · [Original UART frame oracle](../../../tools/uart_rx_oracle.py)

The original synchronous reader received only the public observation history of designated receiver cases, with H equal to one bit period and read latency one edge. It delivered the two original good bytes and rejected the manual program's good B1 terminal. All fault cases returned no pair. The old host binds A7 to a specific verified image. Any new receiver profile would need to bind its own verified image and terminal. Six altered program runs moved the first manual shift by one clock or reused TX0 for frame two. All changed a checked pin result at the expected observation class. [Released host reader](../../../tools/uart_rx_host_service.py) · [Manual TX](manual_tx.asm) · [Manual RX](manual_rx.asm)

The original run compiled at 15:19:59 UTC and finished at 15:20:27 UTC. It used one Icarus implementation, both checked SRAM models and the existing ISA. This is evidence about how these firmware programs use an instruction. It measures neither the area of a chip with that instruction removed nor a general UART's tolerance, throughput, interrupts or asynchronous host. From the repository root in the pinned workbench, select a fresh run directory on H:.

```sh
python3 -B evidence/E0049-review-council/uart-ablation/screen.py build/council-uart-replay
```

## Same-library hardware removal

A separate test changed one decoded period field to zero in an isolated copy of the complete top, which makes the original burst encodings fault. The physical SRAM, loader, manual shift, phase operations and all top-level ports participated in both maps. Both used the same nominal IHP Liberty files, the same ABC script and Yosys 0.69. The kept output names every hardware cell and records the four portless hierarchy annotations separately. [Prospective contract](mapping-contract.md) · [Rejected commands and accounting](mapping-amendment.md) · [Cell counts, areas, libraries and source digests](mapped.json)

| Nominal mapped measure | Reference | Experimental copy |
| --- | ---: | ---: |
| Standard cells / sequential cells | 3,227 / 353 | 2,966 / 353 |
| Standard-cell area (µm²) | 44,717.8158 | 42,587.7858 |
| SRAM area (µm²), one macro | 49,488.4992 | 49,488.4992 |
| Total cell-plus-macro area (µm²) | 94,206.3150 | 92,076.2850 |

Disabling the operation saved 2,130.03 µm² under this mapper, 4.7633% of the logic or 2.2610% including SRAM. The reference here was mapped with its own matched recipe. G4's routed standard-cell area comes from a different flow. The two runs establish neither a tile saving nor a timing or power improvement. [Reference statistics](reference-stat.json.gz) · [Variant statistics](ablation-stat.json.gz) · [Reference map log](reference-map.log.gz) · [Variant map log](ablation-map.log.gz)

On that same source variant the 550 manual UART cases passed and the four original burst probes faulted at the predicted TX or RX instruction with invalid, zero result. The three non-UART G3 groups matched fifty original cases including thirteen deliberate rejections, covering 15,455 observations. This separates the value of the instruction from the cost of its implementation. It also demonstrates a specific compatibility break in programs published for interface 0x22. Changing that interface would need a use case, versioned migration, wider regression and fresh physical acceptance. [Candidate results](candidate-functional.json) · [UART observations](candidate-uart-observations.log.gz) · [Non-UART records](candidate-g3.jsonl.gz) · [JUnit](candidate-g3.xml)

Run from an H: checkout with the repository's pinned workbench and physical PDK available locally. The wrapper requires a new output name and mounts sources and PDK read-only.

```powershell
./evidence/E0049-review-council/uart-ablation/replay-mapping.ps1 -RunName council-mapped-replay
```
