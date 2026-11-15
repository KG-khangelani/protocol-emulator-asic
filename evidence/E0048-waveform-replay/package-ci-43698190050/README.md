# Windows/Linux G5 distribution qualification

Release source: `022834146efcb5f388a4d6ec23b3b705a0df7ef8`.
[Isolated Linux run 43698190050](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43698190050)
uses helper source `672e68aa4d388f43f2de6adf21c3c036dc72e905`; that separate
orphan branch is verification infrastructure and is not merged into main.

The actual pulled, source-identified G4 image replays the complete G5 retained
audit, rejects all five rehashed evidence controls, builds the release package
from immutable Git/CI bytes and runs the standalone smoke test. Windows and
Linux both rebuild the two programs into eight identical artifacts and pass
all twelve checker tests using isolated standard-library Python outside the
repository. The native Windows scratch directory was on H:.

All four actual package files are byte-identical across platforms:
`g5-waveform-replay.zip` (25 members), `g5-original-ci.zip` (unaltered original
qualification transport), `g5-waveform-replay.json` and `g5-SHA256SUMS`.
`verification.json` records full hashes and sizes, image identities and scope.
The original 37-file Linux artifact `14155561054.zip` matches its authenticated
GitHub digest and includes actual commands, logs, image inspection, clone
identity, all four assets and the standalone test outputs. The native Windows
smoke report and compressed logs are retained alongside it.

This establishes package portability and distribution completeness. Public
release downloads and the new matching image must still be checked after the
publisher finishes. No physical checks are rerun or claimed here.
