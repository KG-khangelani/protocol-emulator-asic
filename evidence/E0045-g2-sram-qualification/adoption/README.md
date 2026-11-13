# Local adoption checks

D48 copies all twenty qualified physical inputs directly from the audited
original archive. `production-verification.json` verifies the actual production
files and supporting evidence; `staging.json` proves regeneration produces
identical physical bytes. `adoption.json` identifies the preceding source and
saved pre-adoption file hashes.

The actual default `src/` selection passes Doctor, all 127 repository checks,
style review and generic synthesis in the pinned Linux workbench. Nine of the
repository tests exercise the adopted profile, including rehashed failed or
incomplete physical records, a mismatched netlist pair, changed clock metadata
and changed source/flow/decision files. Stage receipts retain their exact input
hashes. These are pre-commit local screens, not a completed clean CI aggregate.

The atlas passes 23 data/model tests, all fifteen desktop/mobile Chromium tests
and its build. It uses raw source bytes for qualification before normalizing
text for display. The producing physical revision is the actual 94a3082 run;
the adoption's intended publication reference is alpha.6. Two inspected
screenshots and original browser/unit/build reports are retained.

The complete clean default-command CI and verified release/package remain
required. The earlier E0042/E0044 suites and E0045 physical qualification retain
their original identities; these local screens do not replace them.
