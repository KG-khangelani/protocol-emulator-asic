# Fresh G4 program-tool CI

Source: `ae2ac7bf800bd02d83fe62677a56bc4131e98b06`.
Run: [43544749692](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43544749692).
Both the Windows assembly job and the pinned Linux public-program job pass.

The two original verification ZIPs retain 226 members. API size/digest and
completed upload logs bind both archives to their producing jobs. All four
public groups run in each simulator, with 55 cases including 15 expected
rejections. All twenty assembler acceptance tests pass. Both simulators'
normalized observations and all 53 Windows/Linux generated program files
match the qualified G3 records exactly.

All 352 producing verification inputs match canonical Git blobs at the source
commit. The original 351 G3 inputs are unchanged; the sole addition is the G4
acceptance specification. `producer.tar.gz` contains those inputs plus four
historical audit-reference dependencies, with SHA-256 and Git blob IDs in
`producer.json`. The replay reads this frozen bundle and executes no Git or
network command. The original G3 audit, records and 351-input count are unchanged.

The observed CI image configuration digest is
`sha256:cc26d9e866b6dd1b3612a8c6d8e50c31cc962b9ccea4c91c66a83a88eb173b36`.
The completed build log and actual image inspection agree; the run also checks
all locked tool versions. Buildx's auxiliary `.dockerbuild` artifact is not a
verification archive and is explicitly excluded in `verification.json`, with
its API identity retained. API snapshots are parsed JSON; compressed job logs
retain the connector's decoded UTF-8 text. The original ZIP bytes are unchanged.

Replay into a fresh file under `build/`:

```sh
python evidence/E0047-g4-submission-candidate/program-tools/verify.py --output build/g4-program-tools-replay.json
python evidence/E0047-g4-submission-candidate/program-tools/controls.py --output build/g4-program-tools-controls
```

`SHA256SUMS` covers the retained files. Windows and pinned-Linux replays reproduce
the complete audit report. The five controls reject an unfinished workflow,
wrong archive digest, skipped required group, changed program binary and
altered producing-input map. The latter three deliberately rehash the synthetic
archive, API digest and upload log, so rejection must reach the semantic/source
checks. Synthetic records stay under `build/`; they are not presented as real CI.
Windows and Linux produce identical synthetic member bytes and rejection reasons;
their rewritten ZIP container hashes differ. Both control reports retain those
observed hashes, separately from the byte-identical passing audit reports.

This is a fresh CI simulation from separate clean Windows/Linux action
checkouts. No new local-clone simulation was run for the unchanged software.
Replay audits original observations and compares them with G3; it does not rerun
the simulators or every protocol oracle. G4 physical runs, final publication,
analog/silicon results and owner fluency remain separate requirements.
