# Alpha.6 publication and package verification

Release `v0.1.0-alpha.6` uses source `3cd1a62fb00efbf3bcb9d34e6371dfd382e36159`. All eight
tag workflows and their 20 jobs pass.
The publication job independently runs every default-production stage and the
preserved historical SPI release gates. Its original ZIP, job log and API
records are retained; 1,948 original
members and all 329 producing inputs pass semantic/source audit.

All 28 actual release assets were fetched anonymously into
a fresh directory, checked against GitHub's sizes/digests and compared with the
original publication artifact or prepared G2 package. Both checksum lists pass.
Six original physical ZIPs and the original normal-command ZIP are unchanged.
All 1,369 curated
bundle members exactly match the release's committed Git bytes, including the
earlier failed trials and frozen replay inputs.

The public registry manifest/configuration bytes match their declared digests,
the version and source tags resolve to the same image, and Linux amd64
source/version labels match the release. Anonymous HEAD requests verify every
layer's read permission and declared size; layer bodies are not downloaded.
`release-verification.json` records the immutable image digest and boundaries.

The [frozen publication auditor](../release-tools/verify_publication.py) is
identified in `tag-verification.json`. Its initial byte comparison uses the
exact prepared package set. Preserve that set or reproduce it from a clean
checkout of the release tag using the Windows/Python/zlib producer recorded
in `packaging-runtime.json`, then copy this record's
API files, original ZIP and decompressed job log into a new ignored build
directory. Run the auditor there in the pinned Linux workbench to repeat the
semantic/source checks and anonymous release/registry downloads. It refuses
an existing extraction/download directory, preserving failed attempts.

ZIP creator metadata, compression and checksum-line ordering can differ on
another packaging platform/runtime. Cross-platform byte-identical repacking
is not claimed. The original archive checksums, all committed member bytes,
Linux publication audit and frozen qualification replays are separate checks.

This post-publication record is a separate follow-up to the immutable release;
the release does not claim to contain its own completed publication proof.
Physical qualification remains the exact E0045 run at 94a3082, with all twenty
adopted design/flow inputs unchanged. The complete default-command verification
at 75c1e7d has the same 329 inputs as the release commit. G1/P/M0 history and
all protocol, analog, silicon, Fmax and owner-learning boundaries remain.
