# G4 Windows/Linux package identity

Release source `5bdc0e6b6449a829a5da1f8f9a8060257e974843` produced seventeen byte-identical assets in the actual native Windows run and [isolated Linux CI run 43557808053](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43557808053). The Linux workflow source is `50c57ebd0f5243a0267992662af9fafb3cbdfd05`. The actual command receipts, logs, Python/image identities, clean-tree/source checks and all asset hashes are retained.

The original CI transport was authenticated against its API size/digest and completed upload log. `zip-files.json` indexes all 39 original members, including the seventeen assets. `proof/` retains the original non-asset members; `run-summary.json` retains the unmodified original summary. `source/` freezes the actual CI workflow, runner and request from Git. No signed download response is retained.

The 222509831-byte original transport ZIP and seventeen bulk assets are intentionally omitted here to avoid duplication. The original ZIP remains under ignored `build/g4-package-ci-originals/`; its SHA256 is `d2c40400b75c6f909a8aa4348ed92513ac998255c8127c74fe2d2a9a6cbfcca4`. Asset names and identities correspond to the separately prepared v0.1.0 release assets. This packet alone does not reconstruct the original transport ZIP. Publication and anonymous-download proof remain separate gates.

`platform-identity.json` is byte-identical to the completed local `build/g4-package-platform-identity.json`. The sealed native Windows and Linux receipts describe the actual executions; no unused local Docker runner is credited. The Windows log is compressed without changing its original CRLF bytes; decompression matches the original receipt SHA256 and byte count.
