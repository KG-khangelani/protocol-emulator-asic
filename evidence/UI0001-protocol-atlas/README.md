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

## Second bounded increment — local verification

Recorded 2026-10-05 after the first pushed app checkpoint `cff000e`. Original
12/9 results and initial failures above remain historical, not overwritten.

- Doctor: PASS in the existing locked Linux workbench. `Check` rerun: PASS,
  including the existing 18 + 3 + 4 Python cases and immutable workflow refs.
- `npm test` / `.\tools\atlas.ps1 Check`: PASS, now 16 source/reference cases.
  The independently decoded Python oracle agrees on 8,192 edges across 128
  retained-seed (`0xa71a5206`) programs, with reset/disable spans, masked SET,
  WAIT, HALT and invalid/truncated fetch. No production VM path is used.
- `npm run build`: PASS. Node 24 is now required because the test path uses
  native TypeScript stripping; no unsupported Node 22 test claim is retained.
- Final `npm run test:browser`: PASS, 13 Chromium cases in 18.4 seconds locally.
  Added exact page title/nonblank/overlay checks, app console health, Space pin,
  Clear trace, skip-link focus, replay URL/back/refresh, mobile outline/details
  disclosure, mobile signal layer, all four views in both themes/orientations,
  laptop fit and returning from mobile to desktop. The only console warnings
  observed were test-process NO_COLOR/FORCE_COLOR precedence, not app errors.
- Cycle URLs retain program/configuration, accepted/disabled/reset conditions
  and selected row. Reopening never auto-plays. The history is bounded to 256
  UI edges; this is not an engine timeout or proof of wait progress/liveness.
- Evidence displays producing tool versions; TX/RX manifest hashes and required
  stage identities validate. Hypothesis states come from the ledger, not UI
  constants. Missing/changed evidence and explicit failed CI remain fail-closed.
- A provenance audit found a temporary TX false-negative: the older E0016
  record has three successful retained run outcomes but no `implementation_ci`
  field. The exporter now accepts that actual legacy shape only when all three
  recorded outcomes succeed and the manifest/head/stages/hash validate; explicit
  failure still wins. Regression fixtures retain this distinction.
- `.github/workflows/atlas.yaml` pins Node 24.18.0 and direct action commits,
  builds/checks source, runs the JS/Python and Chromium suites, and retains
  screenshot/results artifacts. Exact-head remote results are checked after
  push, not inferred from local passes.

### Fresh visual fidelity / semantic review

The approved private desktop, mobile, cycle and progress concepts and fresh
browser PNGs were all viewed in this pass. Private images and Library identities
are not repository assets. Desktop architecture, cycle and progress captures
match the concepts' native 1536×1024 size. Mobile checks use real CSS viewports
390×844 and 740×390 with native page scroll; the generated 853×1844 concept's
raster size is not treated as a CSS device-width requirement.

| Comparison point | Inspected result / intentional refinement |
|---|---|
| Palette / boundaries | True neutral RGB foundations in both themes; softer surface contrast and substantially fewer borders follow the owner's explicit refinement. No tints, gradients, glows or decorative asset layers. |
| Density / typography | Compact outline, graph and source inspector; 19px main titles, 13px module fields, deliberately sized control text. Text and meaningful trace/focus contrast checks pass in both themes. |
| Layout / mobile | Desktop directed source graph and on-demand inspector retained. Mobile shows one focused module with labelled/tappable dependencies, then collapsed outline/source details; no tiny squeezed full-chip canvas. |
| Graph / evidence truth | Actual named ports determine seven directed relations and 410-bit state attribution. No fabricated zero-valued live program words, data→sync edge or unconditional `uo_out` GPIO bank is copied from generated art. |
| Copy / qualification | Four view names, module identities, exact SET/WAIT/HALT specimen, source context, raw-capture caveat and M0/M1 boundaries agree with the approved contract. Added Theme / Clear trace / URL-history limit labels are functional, not marketing copy. |
| Cycle / progress anatomy | An accessible post-edge table replaces decorative reference strips; full 8-bit GPIO/OE and disabled/reset rows are explicit. Progress uses a compact five-workload × gate matrix plus evidence/learning/deferred context, without duplicated frames or a readiness percentage. |
| Interaction / motion | Intentional dwell, focus, tap/Enter/Space pin, exit, Escape and Clear work; only unrelated strokes fade to 0.6. One 600ms cue at most; reduced motion static. Tracing never runs cycle playback. |

These are recorded refinements to preserve the source-backed semantic contract,
not a claim that generated diagrams are authoritative or that raster pixels
were cloned. No clipping/overlap/material accidental mismatch was found in the
inspected captures. The production build is also runnable through the checked
Windows shortcut; no external hosting, Docker or security change is required.

## Remaining boundaries / next executable action

Review the draft app and its exact-head remote status/artifacts on
[PR9](https://github.com/KG-khangelani/protocol-emulator-asic/pull/9). Actual browser
screenshots are delivered privately through Library; approved concepts stay unchanged.
Keyboard/screen-reader behavior beyond the automated cases,
Safari/Firefox/iOS and deployed hosting are NOT EVALUATED. No new RTL simulation,
synthesis, official GDS or hardware test ran for this UI checkpoint.

E0010 remains ARCHIVED M0 GPIO physical evidence; E0016 is recorded digital TX;
E0018 matches chip source but qualifies only bounded last-byte RX, never complete
UART, FIFO/continuous receive or M1 physical closure. PR8 is not merged and its
external host cache is not CHIP_COMPLETE state. M0 fluency stays PENDING;
H1-H4 stay UNPROVEN. 50 MHz is a TARGET, not Fmax.
