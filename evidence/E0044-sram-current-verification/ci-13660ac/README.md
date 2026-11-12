# E0044 - Complete SRAM normal-command CI

At source `13660ace269c7b0746d8197fe824f76a5f896934`,
[run43309369604](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43309369604)
passes all eight normal verification stages on the exact E0042 SRAM source
and vendor digital models. The original artifact13986941634 is retained:
7,316,407 bytes, SHA256
`658c32f8474f1fd1afa3a245e1cbb3be6affdb8dcfdd31c4a4345aac6f456108`.
The API identity, size and digest, ZIP CRCs and all 1,928 member hashes pass.
The 295 verification inputs are retrieved from the actual producing commit
and match every stage receipt.

Both simulators pass all 30 current groups, all frozen public records and the
high-bank control. All eleven current formal stages and the separate ten-task
historical baseline pass under their original bounds. Generic synthesis has
353 state bits and one real memory black box. The distinct harness waveform
is an RTL smoke test. Repository checks run twice with 116 passing tests each;
the second execution occurs during final collection after the long stages.

The same-job build result, actual container inspection, immutable-image launch,
exit status and tool report identify the producing image as
`sha256:cc26d9e866b6dd1b3612a8c6d8e50c31cc962b9ccea4c91c66a83a88eb173b36`.
This is a measured CI runtime, separate from the local workbench and public
package publication. The earlier local historical-proof timeout remains
incomplete in the parent evidence; this clean run does not rewrite it.

The first replay on Windows is rejected because the frozen counterexample
parser rewrites one derived VCD with CRLF instead of LF. The original ZIP is
unchanged; `failed-windows-audit.json` identifies the exact sole byte change.
The same frozen audit passes on Linux with every artifact hash unchanged.
Run the retained replay in the Linux workbench, using a new output directory:

```text
python3 evidence/E0044-sram-current-verification/ci-13660ac/verify.py --output build/sram-current-ci-replay
```

Full physical qualification, production promotion and milestone publication
remain separate gates.
