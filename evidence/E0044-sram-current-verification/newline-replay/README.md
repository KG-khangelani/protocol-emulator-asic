# E0044 - Preserve counterexample bytes on Windows and Linux

The first Windows audit of the complete CI archive exposed a real portability
bug: inspecting a prefetch counterexample rewrote its derived waveform with
Windows line endings. The original witness and its three wrong-prediction
observations were unchanged, but the retained derived-file hash no longer
matched. The original failed audit and passing Linux audit stay preserved.

The current inspector now performs its single scope-name replacement on bytes.
Replaying the real CI witness twice on Windows and Linux preserves the exact
original derived-file hash and all three observations. Running the frozen old
inspector reproduces the Windows hash change; its Linux result remains stable.
No RTL, proof property, solver setting or counterexample interpretation changes.

The frozen old and corrected inspectors, shared parser, original-run results
and Linux runtime are retained here. Replay uses the original CI ZIP in the
adjacent `ci-13660ac` directory, checks its complete digest, and extracts only
the actual witness and recorded expectations:

```text
python evidence/E0044-sram-current-verification/newline-replay/verify.py --output build/prefetch-newline-replay
```

Use a new output directory each time. The same retained replay has passed
both on the Windows host and in the pinned Linux workbench. The older complete
CI replay still uses its original frozen inspector and remains a Linux replay.
