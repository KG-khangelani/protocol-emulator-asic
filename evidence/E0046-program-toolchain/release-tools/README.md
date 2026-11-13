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
