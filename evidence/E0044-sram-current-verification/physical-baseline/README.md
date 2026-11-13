# Preserve physical comparisons across future production integration

All nine staged profiles keep their exact earlier configuration and source
bytes after moving the common D34 input into a hash-checked archive. These
are G1's P/compact10, G2's od128/literal255/lanes/shared variants, and the three
SRAM physical setups. The frozen pre-change SRAM generator independently
reproduces each staged SRAM configuration byte for byte. The original D34
configuration is taken from G1's qualified `29f4b73` source and still matches
the existing physical lock.

Two new controls verify that an incompatible future production configuration
cannot change historical/SRAM setup, and that changing the archived clock
is rejected. Doctor and all 118 repository tests pass in the locked workbench.
The preparation itself ran on Windows; the retained manifests identify the
modified working tree and exact tested helper bytes. It is not a clean CI run
or new physical qualification.

`rehearsal.tar.gz` retains 358 files: all generated profiles, original generator,
tested inputs, expected source identities, command driver and check log.
The replay validates every file and source/model identity, regenerates the
three configurations with the frozen original function, and checks the actual
118-test log. It does not rerun HDL or physical checks because their inputs
are unchanged.

```text
python evidence/E0044-sram-current-verification/physical-baseline/verify.py --output build/physical-baseline-replay
```

Production remains unchanged. The active official SRAM run still uses its
clean source `232ee20`; this later input relocation cannot change that run.
