# E0012 — Readable M0 waveform qualification

Question: **Can a clean GitHub checkout run the beginner-readable M0 waveform
lab, check every rising edge, and reject a corrupted transition?**

GitHub test run [36128227539](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36128227539)
tested commit `34c07c20b10dae838bfbc1e560fd5527303c3611` on 25 September
2026. The companion [docs run 36128227538](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/36128227538)
also passed.

## What the learning tool does

A waveform is a time-stamped history of signal values. The simulator writes that
history as a VCD file. `make learn-waveform` reruns the real M0 Icarus tests,
reads the VCD without requiring a graphical viewer, and explains selected clock
edges as a table.

The checker evaluates all 1,561 rising clock edges against the specified M0
transition rule:

1. reset low forces the output to `00`;
2. otherwise, enable high adds one modulo 256;
3. otherwise, the output holds its previous value.

It also changes one valid count result in memory and confirms that the same
checker rejects it. This deliberate fault is a *falsification check*: it shows
that the checker can fail for at least one relevant wrong result instead of
merely printing PASS unconditionally.

## Clean-run result

| Observation | Result |
|---|---|
| Learning-stage command | PASS |
| Cocotb tests | 2/2 PASS |
| Simulated time | 31,220 ns |
| Rising edges checked | 1,561 |
| Deliberately corrupted count edge | REJECTED as expected |
| GitHub check annotations | 0 |
| Documentation build | PASS |

The readable rows retained in `learning-waveform.log` include reset, the first
three counts, 8-bit wraparound, hold, resume, and reset taking priority over
enable. `results-learning.xml` is the machine-readable test report.

The exact remote VCD is retained as `m0-learning.vcd.zip` to keep the curated
record small. Its expanded file is 133,455 bytes with SHA-256
`3830ccf44b23226e19e2924d29260167a5f44066e62160e03559499f52fb685c`.
`remote-manifest.json` records the clean checkout, tool versions, stage results,
and source hashes. `result.json` records the run, artifact, hashes, and limits in
one machine-readable summary.

## Claim boundary

This qualifies the learning command on a clean remote checkout and makes one
finite M0 simulation inspectable by a beginner. It does **not** add an
independent chip-behavior proof: the source waveform is the same Icarus
simulation used by the tests. It is not formal, physical, analog, FPGA, or
fabricated-silicon evidence. The VCD includes a generated date field, so its
whole-file hash is an identity for this retained run, not a cross-run
reproducibility expectation.

This record also cannot prove that the project owner understands the result.
That requires the separate owner teach-back checkpoint.
