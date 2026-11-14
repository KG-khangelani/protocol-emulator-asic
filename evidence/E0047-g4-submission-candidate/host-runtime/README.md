# Host runtime interruption during G4

Both official physical runs completed successfully. The host H: volume then
had about 30 MB free. Eight inactive generated-output directories were copied
to available C: scratch space, every file checked by length and SHA256, and
only then were the original H: copies removed. The files remain recoverable
at the destinations in capacity-recovery.json; full individual hash reports
remain beside those copies and under ignored build/. Active G4 and committed
source/evidence stay on H:. No unrelated application data was deleted.

Local Docker inspection requests responded, but new container creation did
not finish. Both repository-digest and exact-config-ID probes timed out; the
intended Linux replay eventually exited125 with a Docker API pipe EOF. Its
genuine invocation, empty/failed output and probe records are retained under
the reproduction's startup-diagnostics directory. A separate direct PowerShell
probe also exited1 with create-API EOF. No local Linux qualification is inferred.
No Docker daemon or unrelated container was restarted or stopped by this task.
The cause of the host behavior is not established.

The remaining Linux verification will use an isolated CI runner with the exact
public alpha.7 workbench image already verified in E0046:
`ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:f487aaf03906535a3187690557ff97ca1707e966b48ae8a99362683b5f68e307`.
Its configuration digest is
`sha256:6f45e71162641466c4e9e08601a383c8a081c06b263114903a181d5f8f971451`.
The workbench Dockerfile and lock are unchanged from that release. This runtime
is recorded separately from the local image and the original LibreLane physical
producer. All original physical results, source identities and acceptance checks
remain required. Actual remote execution proof is a separate pending record.
