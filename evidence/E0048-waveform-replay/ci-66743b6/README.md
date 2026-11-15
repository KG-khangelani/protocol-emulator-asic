# Original G5 qualification at 66743b6

[Run 43697229433](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43697229433),
job 132760362357, passes all required steps. Original artifact
`14155007514.zip` is 2,343,597 bytes with 310 files; its SHA-256 equals the
authenticated GitHub artifact digest. API records, actual job log and the
download receipt are retained here. Signed download URLs are not retained.

The actual pulled G4 image uses manifest `a22fc662...` and config
`21502b12...`, with source label `5bdc0e6...`. Both exact identities are in
`verification.json`; before/after inspection and the pull log are inside the
original ZIP. It runs the unchanged production RTL and hash-checked functional
SRAM models. All 366 producing inputs equal their committed Git blobs.

Primary and distinct clean-clone runs each pass all 21 cases in both Icarus
and Verilator, with five expected rejections. Each simulator records 4,984
loader/runtime observations; all canonical record and trace bytes reproduce.
The twelve independent-checker tests pass in each run. The mandatory G3 guard
passes all 55 public cases per simulator, fifteen expected rejections, twenty
assembler tests, thirteen examples and all 53 frozen generated files.

The ordinary control changes output pin 0 at runtime edge 31; the fault image
changes it at 33. Outputs differ only at edges 31 and 32. Later output edges,
release at 63 and HALT at 64 are identical. The final accepted trigger starts
the waveform at 35 and halts at 88; an absent trigger releases at 35 and halts
at 36. These are the predeclared digital expectations, not adjusted results.

`verification.json` is the replay of original transport, source, commands,
runtime, JUnit, programs, loader operations, complete traces and reproduction.
`audit-controls.json` records five rejected synthetic copies: a changed output
edge, wrong loader address, different image identity, missing JUnit group and
changed oracle source. Their transport and dependent hashes are recomputed;
the semantic checks still reject them. Original evidence remains unchanged.

`windows-comparison.json` additionally compares the retained native Windows
build with Linux. All eight compiled program files and their manifest match.
Eight older source files have only CRLF/LF differences, explicitly listed;
the assembler and both program sources are byte-identical. This is native
assembly evidence, not a clean Windows RTL run. Original native files are in
`../windows-build-66743b6/`.

Replay with standard-library Python from the repository root, choosing fresh
output names:

```sh
python evidence/E0048-waveform-replay/verify.py --directory evidence/E0048-waveform-replay/ci-66743b6 --output build/my-g5-audit.json
python evidence/E0048-waveform-replay/controls.py --directory evidence/E0048-waveform-replay/ci-66743b6 --output build/my-g5-controls.json
```

The replay runs on retained observations and does not pretend to rerun the
simulators. The actual fresh simulator command is documented in the
[example guide](../../../docs/waveform-replay.md).
