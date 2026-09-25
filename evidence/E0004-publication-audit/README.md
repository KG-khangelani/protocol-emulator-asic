# E0004 — Public-release audit

This audit examined commit `b281e1537b69d777fd6e06545e7b594d6479cc0c`
before changing the GitHub repository from private to public.

## Result: ready to publish

- Gitleaks 8.30.1 found no leaks across all 7 commits (128,140 bytes scanned).
- The same pinned scanner found no leaks across the 266,246,282-byte working
  directory, including ignored downloaded workflow artifacts.
- The history contains only the intended small source, documentation and
  evidence files. The largest tracked blob is the 18,746-byte E0002 archive.
- GitHub recognizes the root license as Apache-2.0.
- CI `test` and `docs` both passed at the audited commit.
- Contributor, security, citation and third-party-notice documents are present.
- The known pytest advisory is patched in the source at 9.0.3. GitHub's
  dependency-graph refresh was still queued when this record was written.

The scanner image was addressed by immutable digest:
`ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f`.
The empty JSON reports remain in ignored `build/publication-audit/`; their
interpreted results and exact scope are recorded in `result.json`.

## What this does and does not establish

This is evidence that automated secret patterns and a manual repository review
found no publication blocker. It cannot prove that no sensitive fact exists;
pattern scanners only recognize configured forms, so the source/history review
remains important.

Publication does not certify the ASIC. E0003 still contains a failed gate-level
job, and the repository intentionally says so. Several GitHub Actions also use
branch or major-version references; their resolved E0003 identities are known,
but final pinning waits for a passing integration rather than freezing a broken
one.
