# Alpha.7 publication verification

Release v0.1.0-alpha.7 uses source 33e5e9b286d63317c24eec85ffb0d9ea75f0f8ad.
All nine tag workflows and their 22 jobs pass. The original
publication ZIP contains 1948 members;
all 351 producing inputs match the clean G3 qualification. Its eight default
stages, both thirty-group public suites, current/historical formal checks and
two fresh 147-test repository checks pass semantic/source audit. The preserved
historical SPI gates also pass; their generic P selection does not supersede
G1's separate physical rejection.

All 23 actual release assets were downloaded anonymously into a new directory.
GitHub sizes/digests, both checksum lists and the prepared/original CI bytes
agree. The toolchain ZIP has 73 checked members: eighteen committed source
files, 53 identical Windows/Linux/clean-clone compiled artifacts, its README
and internal manifest. Both original G3 CI ZIPs are byte-identical. Windows
and Linux packaging produce identical five-file downloads. Running only the
extracted distribution reassembles all thirteen examples into the same 52
per-example files and rejects an invalid target without creating output.

The public registry manifest and configuration bodies match their digests.
Version/source tags, Linux amd64 configuration and actual tested image identity
match the release. Every layer accepts anonymous HEAD with the expected size.
Layer bodies were not downloaded; no new physical run is claimed.

The [auditor](../release-tools/verify_publication.py) is identified by
retention.json. To repeat, copy these API files and the original publication ZIP
to a new directory under build/, decompress current-job.log.gz there, preserve
or reproduce the five package assets under build/g3-release-assets/<source>,
then run the auditor in the pinned Linux workbench with --directory pointing
to that fresh directory. It refuses existing extraction/download directories.
The auditor needs Git history containing the release and G3 qualification.
It rechecks source/semantic identities and live anonymous downloads/registry
access. audit-runtime.json records the actual immutable local image used.

This is a separate follow-up to the immutable release, which cannot contain its
own completed publication proof. G2's twenty physical inputs, alpha.6 archives,
G1/P/M0 history and protocol/electrical/owner-learning limits remain unchanged.
G4 submission readiness is separate.
