# Original isolated publication audit

[Run 43702683490](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43702683490),
job `132777024046`, passes at helper commit
`6146f4e8d21ff8af92fd30bf1a9b9bc0f9755305`. It checks the exact release checkout
`022834146efcb5f388a4d6ec23b3b705a0df7ef8`; the helper branch is not merged into
the product source.

The authenticated original `14157406596.zip` has 63 members, 9,452,576 bytes
and SHA-256 `0a9a46fad920a51b64627b2b557e27daf88ebe34da7391e3c6f7fccf2646e6ae`.
The API metadata and actual job log bind its source, job, artifact ID, size
and digest. `verification.json` records the native transport/receipt audit.

The original contains the actual runner, request, auditor, command receipts,
logs, image inspections, publisher originals and anonymous public downloads.
The runner, auditor and all nine publication inputs match the helper's Git
blobs. The auditor also matches committed main source `00712f1`; its SHA-256
is `c98bac2851de457a8dfc0998233060f3eb4ed090912dc188c5838619e9407995`.
Before/after inspections bind the previously verified G4 runtime:
`sha256:a22fc6626bc4f61b52cd6a32793cec86f718f0943d078ad03cfbf8dc7932af88`,
configuration ID `sha256:21502b121379e64bf296ca06cceb96cf31d7e33c6b40a9152af5d472287fd06a`.

The actual public verification has SHA-256
`ca2efb39a316416c7c69f5d6404f984660ed48fad2fd23a554bb857f1002ae35` and is retained
in [publication/](../publication/README.md). All four downloaded G5 files also
match the earlier native Windows package byte for byte.

`zip-files.json` records every original member. The frozen runner/auditor and
the actual native receipt-audit script are retained as gzip files. The latter
was executed while the connector's temporary artifact URL was valid; that
URL is not retained here. `retention.json` seals the captured record files;
this README is explanatory material added afterward.
