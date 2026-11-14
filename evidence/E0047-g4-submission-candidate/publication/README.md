# v0.1.0 publication verification

Release `v0.1.0` uses source `5bdc0e6b6449a829a5da1f8f9a8060257e974843`.
All nine tag workflows and their 22 jobs pass. The original
publication ZIP retains 1948 members;
all 352 producing inputs match the release Git bytes,
including the unchanged 351 G3 inputs. Its eight normal stages, both public
RTL suites, current/historical formal checks and two fresh 147-test repository
checks pass semantic/source audit. Historical SPI gates keep their original scope.

All 35 actual release assets were downloaded anonymously into a fresh directory.
GitHub sizes/digests, both checksum lists and the prepared/original CI bytes agree.
The submission bundle has 435 checked members.
Native Windows and isolated Linux CI packaging produce identical seventeen-file downloads.
Running only the extracted assembler and example sources rebuilds all thirteen
examples into the same 52 per-example files and rejects an unsupported target.

The actual Linux package proof is
[run 43557808053](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43557808053)
at CI execution source `50c57ebd0f5243a0267992662af9fafb3cbdfd05`.
The publication audit is
[run 43562510340](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43562510340)
at CI execution source `0cc61c3620a7e13003bef02a912118b147894758`.
Both operate on the release source above; those isolated execution commits
are separate identities and are retained with their source and API envelopes.

Both fresh physical qualifications are replayed from the twelve original ZIPs
downloaded from this release. All 3458 original physical archive members,
producer inputs, semantic results and retained UART landmarks pass audit.
The complete reproduction record is recomputed from those downloads. Only
standard GDS timestamps differ; netlists, geometry, timing/area and recorded
public observations agree. G2 continuity is separately recomputed from its
original submitted layout. The fresh program-tool CI audit is also rerun from
the downloaded bundle with its original archives and frozen source inputs.

Public registry manifest/configuration bodies match their digests. Version and
source tags, Linux amd64 configuration and actual tested image identity match
the release. Every layer accepts anonymous HEAD with its expected size. Layer
bodies were not downloaded; this does not claim a separate full image pull.

The [auditor](../release-tools/verify_publication.py) is identified by
retention.json. To repeat, copy these API files and the original publication ZIP
to a fresh directory under build/, decompress current-job.log.gz there, and
rebuild the seventeen package assets from the release source using
`../release-tools/package.py --source 5bdc0e6b6449a829a5da1f8f9a8060257e974843 --out build/g4-release-assets/5bdc0e6b6449a829a5da1f8f9a8060257e974843`.
Run the auditor in the pinned Linux workbench with --directory selecting the
fresh directory. It needs repository Git history, refuses existing extraction
directories and rechecks live anonymous downloads/registry access.
audit-runtime.json records the actual isolated Linux CI invocation, source and
Python runtime. Its audit image is the verified public alpha.7 workbench,
distinct from the newly published release image checked by the auditor.
The captured Windows helper/receipt and both actual remote runner sources are
retained; retention.json binds their raw logs, source hashes and authenticated
CI envelopes. No unused local Docker launcher is credited with this work.

The sealed package CI proof intentionally omits its large transport ZIP and
seventeen duplicate asset bodies. It retains the verified API size/digest,
upload log, complete member map, source, actual command receipts and platform
comparison; the final release supplies those asset bytes. The separate small
publication CI proof retains its original curated ZIP. Both proof directories
are named and sealed by retention.json and the completion audit.

Large original physical ZIPs are already sealed in the per-run evidence;
the distribution bundle is deterministic from committed source and evidence.
This directory retains their independently downloaded identities and complete
member maps without duplicating the bulk archives again.

This is a separate follow-up to the immutable release, which cannot contain its
own completed publication proof. G1-G3 history, twenty physical inputs and
protocol/electrical/owner-learning limits remain unchanged. No competition
entry, hardware expenditure, fabricated-chip or owner-fluency result is claimed.
