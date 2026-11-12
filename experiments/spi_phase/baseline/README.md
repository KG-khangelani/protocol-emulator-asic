# Frozen E0020 baseline

These five RTL files are byte-identical to `src/` at E0020's source commit
`ae13f6bfcfd3fe21cd937768bc9e1151f441379c`. Their hashes are checked against the
original E0020 result on every experimental build.

Historical SPI variants and the G2 comparison must remain reproducible after
production eventually changes. They therefore read this archive explicitly.
The archive is not a second production source list or a new qualification.
Existing generated candidate hashes, historical results and failure claims
remain unchanged. Current production RTL and its ordinary checks still use
the repository's `src/` directory.
