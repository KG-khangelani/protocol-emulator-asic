# UI0001 — first working Protocol atlas candidate

Date: 2026-10-05. Rung: **browser / independent reference inspection only**.
This is not an ASIC experiment or new RTL/physical evidence. It changes no
production RTL, official pins/config, tile allocation, ISA or owner learning.

The approved app direction is implemented as real HTML/SVG controls, not raster
concepts: architecture, reference cycles, evidence and progress; soft neutral
light/dark themes; no repeated/nested card borders; source-backed inverse trace.

## First local checkpoint

Tested on Windows with Node 24.18.0, npm 11.8.0, React 19.3.0, TypeScript 7.0.2,
Vite 8.3.2 and Playwright 1.63.0 / Chromium 153.0.8010.12 (revision 1243).

- `npm run data:check`: PASS. Five chip-file hashes match the retained E0018
  manifest. 261 + 108 + 25 + 16 = 410 sequential state bits are derived; seven
  named directional relationships are checked against source.
- `npm test`: PASS, 12 source/reference cases. Includes changed source, missing
  evidence and wrong-wiring rejection, exact approved edge table, WAIT
  0/1/2/65535, reset/freeze, every SET mask and sticky HALT/FAULT.
- `npm run build`: PASS after the initial TypeScript failure below.
- Existing locked workbench `Check` (`make check`): PASS, including 18 M1 model,
  three RX oracle and four waveform-provenance tests. Doctor passed at the
  preceding design checkpoint. These are not fresh RTL or physical runs.
- `npm run test:browser`: PASS, 9 real Chromium cases in the second run.
  Search/select/source links, label layer, zoom/fit, dwell/focus/pin/exit/Escape,
  labels at full opacity, inverse strokes at 0.6, both themes, system/persistence,
  denied storage, reduced motion, copy/refresh/back, exact reference specimen,
  reset/disable/invalid program, evidence/progress limits and mobile portrait /
  landscape are checked. Normal text >=4.5:1 and meaningful focus/path >=3:1
  against named neutral surface tokens in both themes. No document-width
  overflow in tested mobile viewports (390×844, 740×390).
- Actual desktop light/dark, cycle/progress and mobile captures were inspected
  locally under ignored `build/atlas-qa/screenshots/`. They are browser renders,
  not generated concepts or physical chip images.

## Failures retained, not rewritten

1. Initial build: TypeScript TS2882 could not resolve the CSS side-effect
   import. Added explicit `vite/client` type declarations; build rerun passed.
2. First browser run: 7 passed, 2 failed. Opacity was sampled mid-transition
   (0.605697 rather than settled 0.6); assertion now polls for the settled value.
   Scenario selection timed out because its native label included option text;
   an explicit accessible name was added. Failure report/trace copy retained
   privately under `build/atlas-qa/initial-failure/`; second run passed 9/9.
3. Read-only host process enumeration was denied. It was not counted as a
   successful runtime check; the project browser harness instead owns its
   loopback server and refuses an occupied port.

## Remaining boundaries / next executable action

Broaden independent JS/Python reference agreement and cycle URL restoration;
improve mobile outline/details disclosure; add pinned frontend CI and inspect
fresh captures. Keyboard/screen-reader behavior beyond the automated cases,
Safari/Firefox/iOS and deployed hosting are NOT EVALUATED. No new RTL simulation,
synthesis, official GDS or hardware test ran for this UI checkpoint.

E0010 remains ARCHIVED M0 GPIO physical evidence; E0016 is recorded digital TX;
E0018 matches chip source but qualifies only bounded last-byte RX, never complete
UART, FIFO/continuous receive or M1 physical closure. PR8 is not merged and its
external host cache is not CHIP_COMPLETE state. M0 fluency stays PENDING;
H1-H4 stay UNPROVEN. 50 MHz is a TARGET, not Fmax.
