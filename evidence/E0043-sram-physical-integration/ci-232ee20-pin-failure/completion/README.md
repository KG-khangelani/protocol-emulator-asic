# Completion of rejected official run 43337581691

The final gate-level job passes all eighteen public UART/SPI/I2C groups on
the actual submitted netlist. The 1,052 SPI, 1,160 I2C, four boundary and
36 abort records exactly match the frozen references. Both Windows and
native Linux replay the 477 additional original archive files successfully.

This completion supplements the earlier snapshot without changing it. The
run remains **rejected** because the independent power-port precheck failed
with 148 LEF errors. Its GDS and netlist jobs pass; its precheck job fails.
The verifier explicitly checks that aggregate qualification rejects this run.
D47's separate run must pass all gates before production adoption.

The final API snapshots, both original ZIPs, full gate-level log and per-file
index are retained here. Verification uses the producing revision's frozen
helpers and reference records already retained in the parent directory.

```console
python evidence/E0043-sram-physical-integration/ci-232ee20-pin-failure/completion/verify.py --output build/sram-pin-run-completion-replay
```

These are zero-delay digital circuit tests. Timing and manufacturing checks
have separate evidence; successful simulation does not erase a physical rejection.
