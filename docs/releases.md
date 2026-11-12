# Releases and packages

The [Releases](https://github.com/KG-khangelani/protocol-emulator-asic/releases)
page contains versioned research snapshots. The linked
[workbench package](https://github.com/KG-khangelani/protocol-emulator-asic/pkgs/container/protocol-emulator-asic-workbench)
contains the pinned Linux amd64 verification tools. A release is not a tapeout,
silicon result, new physical qualification or owner fluency sign-off.

## Automatic updates

The [publish workflow](../.github/workflows/publish.yaml) builds and tests the
workbench when its inputs or publication workflow change on main. It publishes
the exact tested image to GitHub Container Registry, using the workflow's
repository token. No personal package token is stored in the repository.

- `main` tracks the most recently verified workbench update.
- `sha-<full source commit>` identifies the source used for a publication.
- A version tag, such as `v0.1.0-alpha.1`, publishes a matching image tag and
  GitHub release after the verification ladder and focused SPI gates pass.
- The publication manifest records the immutable registry digest, source commit,
  toolchain-lock checksum, verification run and explicit qualification limits.
  Use the digest for reproducibility; tags are convenient names.

Versioned releases require notes at `docs/releases/<tag>.md` and a commit
reachable from main. Published release versions are not overwritten; corrections
use a new version. Alpha/beta/rc tags are marked as prereleases. Ordinary source
or documentation commits do not create a milestone release.

## Publish the next milestone

1. Update the evidence and current-state documentation.
2. Write `docs/releases/vX.Y.Z-alpha.N.md` with verified results and remaining
   limits; commit and push it with the milestone.
3. Tag that exact commit and push the tag:

   ```powershell
   git tag -a vX.Y.Z-alpha.N -m "Describe the verified milestone"
   git push origin vX.Y.Z-alpha.N
   ```

The workflow validates the tag, runs `workbench.sh All` (tool versions, model
checks, lint, both RTL simulators, formal checks and synthesis), and reruns the
program-sensitivity and four-mode SPI screens, the held-program proof and
its counterexamples, the phase1 capacity/rejection screen, and the timed GPIO comparison for releases. Publication stops on
a failed check. Release assets include the lock, manifest, checksums and scoped
SPI results (including the held-program proof, phase1 capacity screen and timed comparison with its seven supporting gate records); source archives and the checked-in evidence come from the tag.
The separate full experimental CI and official CMOS5L flows retain their own
evidence boundaries.

To retry an unpublished version after an infrastructure failure, rerun its failed
workflow. For a deliberate workbench rebuild, dispatch `publish` on main.
Do not move an already published version tag. Each branch/tag has its own
publication queue so a workbench update cannot cancel a waiting milestone release.

## Use the published workbench

From a matching source checkout, take the image digest from the release's
`publication.json`:

```powershell
docker pull ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:<digest>
docker tag ghcr.io/kg-khangelani/protocol-emulator-asic-workbench@sha256:<digest> protocol-emulator-asic-workbench:2026-07-29
.\tools\workbench.ps1 Doctor
.\tools\workbench.ps1 All
```

The local alias must match `developer_workbench.image_tag` in that checkout's
`tools/workbench/toolchain.lock.json`. The image supplies tools; mount the source
through the existing wrapper. It does not embed a private workspace or a compiled
chip design. The build recipe is Apache-2.0; bundled tools retain their upstream
licenses.

GitHub creates new container packages with private visibility even for a public
repository. After first publication, the package owner sets **Package settings >
Change visibility > Public** once for anonymous pulls. Later versions inherit
that package setting. See
[GitHub's visibility documentation](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility).
