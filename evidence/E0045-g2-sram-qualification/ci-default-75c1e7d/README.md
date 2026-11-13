# Actual default-production CI

Run 43361418837 at `75c1e7d9eec80541b7b675a20f0557b8c1b22126` passes all eight normal
verification stages using the actual `/workspace/src` files. No alternate
source-directory setting or experimental generator supplies the production RTL.
The complete current suite passes thirty groups in each simulator, and the
current formal properties and independent historical baseline pass. Both fresh
repository-check executions pass 127 tests.

The original ZIP contains 1,922 files. The frozen
audit verifies its GitHub digest/size, every member, all 329 producing
input files, semantic results, container exit and exact built image identity.
The retained production guard binds all twenty adopted physical inputs to
E0045's separately qualified layout. This job does not rerun physical design.

Replay in the pinned Linux workbench, with the checkout mounted at `/workspace`:

```sh
python3 evidence/E0045-g2-sram-qualification/ci-default-75c1e7d/verify.py --output build/default-production-replay
```

Use a new output directory. The frozen waveform parser writes native line
endings, so this replay requires Linux, as did the preceding E0044 audit.
`inputs.tar.gz` supplies the original producing source and verification code;
the replay compares the complete report and original member hashes.

A fresh pinned-Linux replay passes and reproduces the complete report and all
1,922 member hashes exactly; `verification-linux.json` and its log retain it.
