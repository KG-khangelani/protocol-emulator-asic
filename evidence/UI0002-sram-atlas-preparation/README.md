# SRAM atlas preparation

The atlas now derives 353 register bits, 8,192 physical SRAM bits and 128 logical
program words from the retained E0042 candidate. It traces the real prefetch
connection and separates register state from memory capacity. The original
eight-word production source remains selected at this checkpoint.

The production-evidence reader requires the complete physical result, all three
successful jobs, exact staged input hashes, combined regression, normal-command
verification and the corrected two-simulator netlist result. Missing or failed
records cannot borrow the old qualification. The positive production branch
still requires validation after actual qualified adoption.

`qa.json` identifies the tested working-tree files and retained reports. All 22
data/model tests, 15 Chromium browser tests, the application build and the
additional actual-candidate desktop/phone preview pass. The preview checks
353/8,192-bit accounting, the 128-word caption, the real prefetch wire,
non-overlapping sequencer text, mobile scrolling and console errors. Its two
screenshots were inspected. Repository checks separately pass all 118 tests.

`browser-missing.json.gz` preserves the first failed browser launch: the locked
browser was absent. Installing Chromium 153.0.8010.12 under ignored `build/`
resolved that environment issue; the full rerun is `final-browser.json.gz`.

Reproduce the normal checks with `cd web`, `npm ci`, `npm run build`, `npm test`
and `npm run test:browser` after installing the locked Playwright browser.
`preparation.mjs`, `preview.config.mjs`, `preview.spec.mjs` and
`candidate-data.json` retain the temporary pre-adoption experiment as executed;
their original paths are under `build/`, and their screenshot destination was
`H:/CodexArtifacts/g2-sram-atlas`. They are historical inputs, not a future
production qualification command.

This is browser/data evidence only. It does not promote production, qualify
physical hardware, establish owner fluency or demonstrate other browsers or
user devices.
