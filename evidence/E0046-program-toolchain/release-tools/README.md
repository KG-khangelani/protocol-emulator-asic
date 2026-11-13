# G3 milestone packaging

`package.py` first replays the frozen clean-checkout/CI audit, then requires
every one of its 351 producing inputs to match the current committed Git bytes.
It refuses uncommitted tracked changes and an existing output directory.

```sh
python evidence/E0046-program-toolchain/release-tools/package.py --out build/g3-release-assets
```

The resulting five assets are the standalone source/compiled toolchain ZIP,
the two untouched original CI ZIPs, a source-bound manifest and separate G3
checksums. The toolchain ZIP uses stored entries, fixed timestamps and explicit
Unix file metadata; its bytes do not depend on a platform's compression library.
Its 18 Git-source files and 53 compiled files are identified individually.

The original physical archives remain in alpha.6. This package preserves the
qualified interface and hardware source, rather than relabeling a software
build as new physical evidence. Publication uses the existing locked release
workflow and matching image. After upload, audit actual anonymous downloads,
original CI/member identities, all release-tag jobs and registry identities
before closing G3.

`verify_publication.py` performs that post-publication check in the pinned Linux
workbench. It verifies the original publication archive, all eight normal
production stages and historical release gates, all 351 source inputs, actual
anonymous asset downloads, bundle members, annotated tag/commit identity,
all nine tag workflows and the public registry's manifest/configuration and
layer access. It refuses an existing extraction or download directory.

The [retained record](../publication/README.md) includes the five exact prepared
G3 files, original publication ZIP, API responses and compressed job log.
Copy its five `g3-*` assets to `build/g3-release-assets/33e5e9b286d63317c24eec85ffb0d9ea75f0f8ad/`;
copy the API files and original publication ZIP into a new build directory and
decompress `current-job.log.gz` there. From a checkout containing the auditor
and release Git history, run:

```sh
python3 evidence/E0046-program-toolchain/release-tools/verify_publication.py --directory build/g3-publication-replay
```

To recreate the prepared package instead, run `package.py` from a clean checkout
of the immutable alpha.7 tag. The recorded Windows and Linux five-file packages
are byte-identical. A later checkout's changed release identity must not be
presented as the original package.
