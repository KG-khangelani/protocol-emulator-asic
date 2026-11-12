# Audited SRAM CI at 95120d8

[Run 43287092840](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43287092840)
passes all three jobs at exact source
95120d87c3f09b7598f362f0bb0e66772112d3f7. The three original ZIPs retain 1,359
files. Their downloaded sizes and SHA256 values match GitHub metadata and
each producing job's upload log. Forty-five retained inputs bind the tests,
workflow, runtime lock, source manifest and unchanged reference observations.

The independent replay examines the actual proof models, reset comparisons,
full 8,192-bit memory, 18 assertions, four covers, deliberately faulty store
simulations and stale-lane counterexample. It recomputes both exact 30-group
test selections, all 1,052 SPI and 1,160 I2C records, four boundaries, 36 aborts
and the 44-byte bank control. Icarus completes in 942.497 seconds and Verilator
in 465.878 seconds, each inside the original 1,800-second limit.

Each original runtime observation reports image
cc26d9e866b6dd1b3612a8c6d8e50c31cc962b9ccea4c91c66a83a88eb173b36.
Each same-job log binds it to the loaded build configuration, exact source,
locked doctor check and `--pull=never` execution. This is a CI observation;
the earlier local regression's missing exact-image receipt stays documented.

`proof_checks.py` carries forward the E0042 semantic assertions against these
actual CI files. Only comparisons to local summary copies and unrelated
historical failed attempts were removed; the retention script records that
extraction. No local proof or simulation result substitutes for CI evidence.

```console
python evidence/E0042-sram-prefetch-screen/ci-95120d8/verify.py --output build/sram-ci-replay
```

This closes the clean-checkout SRAM proof/protocol CI gate. Physical
qualification and production promotion remain separate and open.
