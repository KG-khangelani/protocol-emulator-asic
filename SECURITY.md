# Security policy

Please report a suspected vulnerability privately through this repository's
GitHub **Security → Report a vulnerability** path. Do not open a public issue
containing credentials, tokens, private artifact links or exploit details.

The repository must not contain:

- access tokens, passwords, signing material or `.env` files;
- proprietary PDK data or foundry-confidential material;
- private personal/work records unrelated to this project;
- unreviewed binary IP whose source and license cannot be inspected.

Generated open-PDK data and bulk tool output belong in ignored local storage or
time-bounded CI/release artifacts. Curated evidence committed to the repository
must contain hashes and provenance without embedding secrets.

Security reports do not imply that the open-source EDA flow provides foundry
signoff or protection against malicious fabrication. Those are outside the
claims of this project unless separately evaluated.
