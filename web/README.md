# Protocol atlas

Local React/TypeScript inspection app. No chip/device control, API key, backend,
telemetry or deployment. Source geometry is schematic, not a physical floorplan.

Node 24 is required (native TypeScript stripping for model tests); 24.18.0 is
the tested version. Python 3 runs the independent reference oracle. Exact dependency versions and
lockfile are committed. Run from this directory:

```powershell
npm ci --ignore-scripts
npm run data:check
npm test
npm run build
npm run dev
```

Open `http://127.0.0.1:5179`. Stop with Ctrl+C. `npm run preview` serves the
production build on the same loopback port, never concurrently with `dev`.
From the repository root on KhanCreate, `.\tools\atlas.ps1 Start` builds and
serves the checked production app. `Check` runs source/reference checks and
builds; `Build` builds only. The shortcut does not install dependencies, change
execution policy, start Docker or kill any existing server.

`npm run data` deterministically exports only public source/evidence. Review
changes before committing. State counts are derived from declared nonblocking
register assignments; wiring is checked against actual top-level named ports.
This is a deliberately bounded extractor, not a general Verilog parser. Changed
chip source or missing E0018 evidence never retains current-source PASS.

## Browser checks

Use a project-local browser cache, not a global browser/security change:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Resolve-Path ..) 'build/atlas-browsers'
npx --no-install playwright install chromium
npm run test:browser
```

Linux equivalent: `export PLAYWRIGHT_BROWSERS_PATH="$PWD/../build/atlas-browsers"`,
then the same npm commands. Reports, traces and screenshots stay under ignored
`build/atlas-qa/`. The harness requires port 5179 to be free; it never reuses or
kills an existing server. Close only a server you started yourself.

Architecture: search/select modules, inspect source, toggle signal labels,
zoom/fit, hover or focus a relationship, click/Enter/Space to pin, Escape/Clear
to restore plain view. Unrelated strokes gently fade; labels stay fully legible.
Reduced motion is static. Theme defaults to the system and persists explicit
light/dark choices; System follows preference changes.

Cycles: explicit independent SET/WAIT/HALT reference playback. Reset is
synchronous and wins over disable; WAIT counts only accepted edges. Tables show
full stored value/OE, not analog waveforms. This subset does not model the
loader, synchronization, LOOP/SHIFT or live measured RTL. Evidence and Progress
retain separate revision, workload, physical and learning boundaries.

Cycle links preserve the bounded program, up to 256 sampled edge conditions,
enable/reset controls and selected row. Reload never starts autoplay. This UI
trace bound is not a chip timeout; the full WAIT(65535) boundary is independently
tested. The retained seed `0xa71a5206` checks 128 separately decoded programs
against the Python oracle on 8,192 edges. `ATLAS_PYTHON` can select the Python
executable; absence is a failed check, never a skipped pass.

This is a versioned snapshot, not live CI or branch polling. PR8 remains a
separate unmerged draft. M1 physical results and owner fluency are not promoted.

See [UI0001](../evidence/UI0001-protocol-atlas/README.md) for actual checks and
the [approved contract](../docs/specs/protocol-atlas.md) for pending obligations.
