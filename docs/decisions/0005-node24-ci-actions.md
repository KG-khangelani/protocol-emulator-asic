# D5 — Move Docker CI orchestration to Node 24 actions

Date: 2026-09-25. Status: adopted and qualified by E0011.

Need: GitHub run 36124428730 passed, but GitHub annotated both Docker actions
because their pinned versions declared the retired Node 20 action runtime.
GitHub temporarily forced those actions onto Node 24. Relying indefinitely on
that compatibility override would make the effective runtime differ from the
runtime declared by the pinned action source.

Decision: update only the two Docker orchestration actions to current immutable
release commits whose `action.yml` files declare `using: node24`:

- `docker/setup-buildx-action` v4.4.1,
  `f87e5991a6d7451dcb8d9637bfbc97413f497069`;
- `docker/build-push-action` v7.4.0,
  `c3c9e263c25d99ce0380d002d59b67737d91b0dc`.

Both commits are reported as verified by GitHub. The v4/v7 action manifests
retain every input used here: build context, Dockerfile, load, tag, and GitHub
cache configuration. The workbench Dockerfile, EDA packages, dependency hashes,
test commands, and physical-flow snapshot do not change.

In plain language: these actions prepare and run Docker Buildx in GitHub CI;
they are not the chip compilers inside the container. Even so, the upgrade is
not accepted on inspection alone. A clean push run must build the locked image,
pass the full seven-stage ladder, collect evidence, upload the artifact, and
finish without the Node 20 deprecation annotation.

Consequences:

- The repository records the declared action runtime instead of depending on a
  GitHub compatibility override.
- Qualification is scoped to the fast CI lane; it does not alter or rerun the
  already qualified CMOS5L physical snapshot.
- Future action upgrades remain explicit lock changes followed by clean CI.

Qualification: clean GitHub run 36124783158 built the unchanged locked image,
passed all seven fast stages, collected and uploaded evidence, and returned no
check annotations. E0011 retains the run and action-manifest identities.

Rejected: leaving the warning indefinitely, following mutable v4/v7 tags, or
changing the workbench tool versions at the same time as the runner upgrade.
