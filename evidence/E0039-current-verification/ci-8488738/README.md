# E0039 current-command CI completion

At source `848873898c9b02947b414a6c9211738a93b7c829`, test run43267588725
passes all three jobs. The current-candidate job131371975025 completes all
eight normal verification stages on the exact frozen D39 source.

The original artifact13971730764 is retained as `current-candidate.zip`:
6,959,083 bytes, SHA256
`804dd04cbaad570b2a92d4ecb0411743a887a547297695272da3be90483e6610`.
The API digest/size/run/source identity, ZIP CRCs and all 1,532 member hashes
are checked. `inputs.tar.gz` contains the 250 exact verification inputs
retrieved from that commit and matched against every stage receipt.

Replay checks all 30 groups in each simulator, exact public records and the
high-bank control; complete-chip proof/reset and current instruction/support
checks; the separate ten-task historical formal baseline; actual generic
netlist counts; and the separately labelled RTL harness smoke test. The current
temporal proof finishes in 108.405 seconds within its unchanged 300-second
budget. It does not relabel the earlier local timeout as a pass.

Repository checks execute twice, with 114 passing tests each. Collection's
second execution occurs after the long stages, verifying the fresh-check fix.
Decoded CI logs retain the image build/config digest, the same-job command
using the loaded image without pulling, exact in-container tool identity and
artifact-upload identity. This is a CI runtime observation, not a new public
container publication.

```text
python evidence/E0039-current-verification/ci-8488738/verify.py --output build/current-ci-replay
```

No physical result is inferred. D39's original routing rejection, the earlier
local timeout, production source and G1's qualification remain unchanged.
