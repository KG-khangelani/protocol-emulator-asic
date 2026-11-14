# Rejected first G4 package portability attempt

Release source `6140001b47a6643471a1e4c4b361cb2f52975368` and [Linux run 43556669842](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43556669842) produced seventeen assets. Direct byte comparison finds sixteen identical assets. Only `g4-SHA256SUMS` differs, with the same sixteen name/hash pairs in a different order.

WindowsPath sorting is case-insensitive; PosixPath sorting is case-sensitive. `GDS_logs` and `gatelevel_test_results` swap positions for each physical run. The required correction is an explicit `key=lambda path: path.name`, followed by a newly committed source and fresh Windows/Linux package runs. This retained attempt remains rejected.

Both actual checksum files, all asset identities, original CI API records/upload log, frozen workflow source, original non-asset proof members and native Windows invocation/log are retained. `zip-files.json` indexes every original transport member. The authenticated 222337111-byte original ZIP and seventeen bulk assets remain in ignored build storage and are intentionally omitted here to avoid duplication. Its API/upload-bound SHA256 is `00582f4d69c4c7d2693245df4180b2b5190cbe41bb819411d7e277b344e7777b`. This small packet does not reconstruct the original transport ZIP. Public release verification is a separate gate.

The original Windows log is retained as windows/windows-package.log.gz to preserve its exact CRLF bytes through Git normalization. Decompression matches the unchanged original invocation SHA256 and byte count. The original build log is unchanged.
