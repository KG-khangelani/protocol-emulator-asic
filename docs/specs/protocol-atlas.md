# Protocol atlas design and implementation contract

Date: 2026-10-05. Status: **direction APPROVED; first working app candidate**.
The initial documentation checkpoint contained no application. The owner approved the revised direction with
dark mode, softer surface contrast and substantially fewer borders. Publishing
this contract is not implementation, protocol qualification, physical evidence
or an owner-fluency result. PR8 integration remains separately deferred.

This is a source-backed inspection tool for the protocol-emulator project, not
a hardware controller. Its first release must use repository source and retained
evidence; no device driver, live chip connection or external telemetry is in
scope. Private reference photos and generated review images are not public
repository assets and must not be copied into this document or a shipped UI.

## Information architecture

The four coordinated views are Architecture, Cycles, Evidence and Progress.
They share a compact header, source-revision context, navigable outline and
source/evidence inspector. Controls and text must be real HTML/SVG UI, not a
raster screenshot masquerading as an application.

- Architecture: inspect CHIP_COMPLETE modules, named ports and relationships;
  select a module or relation to expose source and bounded semantic details.
  Geometry is schematic, never a physical floorplan or area proportion.
- Cycles: step an explicitly labelled independent reference model, with a
  decoded program, accepted-edge table and selected-edge inspector. Model
  playback is not an RTL waveform or hardware capture.
- Evidence: inspect the workload, producing revision/tool/run, assumptions,
  verification rung, retained artifacts and limits of each result.
- Progress: a workload-by-gate matrix, not a completion percentage. Keep
  engineering, physical closure and owner learning separate.

On desktop, each region is internally dense: outline, graph/table, inspector.
On mobile, show a focused module or edge and disclose outline/layers/details
without squeezing every desktop panel into one miniature canvas. The selected
item, revision and proof caveat remain visible when details are collapsed.

## Neutral palette and compactness

The owner approved the coordinated direction and the following refinements.
Implement it without another concept-approval round; verify the actual UI.

| Role | Allowed treatment | Meaning independent of colour |
|---|---|---|
| Light foundation | Neutral `#F5F5F5`/`#FAFAFA`/`#FFFFFF` | Low surface contrast, purposeful whitespace |
| Dark foundation | Neutral `#191919`/`#202020`/`#262626` | Soft layers, not harsh black/white slabs |
| Ordinary text | Achromatic high-contrast text, muted secondary labels in both themes | Legible titles, labels and values |
| Rules | Neutral gray; stronger contrast for meaningful boundaries/focus | Group boundaries and focus outline |
| Selection | Small `#005FCC` rule, cursor or selected path only | Selected label, pointer, underline or outline |
| Recorded PASS | Small `#177245` check glyph only; neutral text | Check plus explicit PASS and qualified scope |
| Pending/not run/not evaluated | Neutral label with hollow circle or dash | Explicit state; not a failure |

Foundation RGB channels must be equal. No navy ordinary text, warm/cool surface
tint, large chromatic module/row wash, gradient, glow, decorative rainbow,
colored button fill or arbitrary accent link. Links are underlined; controls
are neutral and do not require a box around every control. Another hue requires an explicit necessary
semantic role; do not invent a warning or failure to justify decoration.

Keep desktop headings modest (about 17-19px), ordinary text readable (about
13-14px), rows about 26-32px and internal region padding about 4-8px. Use
purposeful white gaps, typically 16-24px, BETWEEN compact functional regions.
Do not create oversized cards, sprawling headings or empty padded expanses.
These are proposed tokens, not permission to squeeze or clip text.

Mobile visible controls stay compact but have at least 44px touch hit areas
or an equivalent accessible list control. Provide strong keyboard focus,
non-hover labels, text alternatives and native scrolling. Require 4.5:1 normal
text contrast and 3:1 meaningful non-text/focus contrast; light grid rules are
not the sole encoding of a meaningful boundary.

Use far fewer borders than the static review images: alignment, whitespace,
restrained typography and subtle grayscale surface changes establish hierarchy.
Avoid repeated boxed cards, double/nested borders and harsh black/white slabs.
Reserve separators for actual relationships or necessary table legibility.
Soft SURFACE contrast must not weaken text, meaningful paths or keyboard focus.

Provide a theme switch, system-preference default and persisted explicit user
choice. System mode follows preference changes; storage failure falls back
safely. Semantic selection/PASS hues may adjust luminance for dark mode while
preserving the same meaning. Verify text, focus and trace contrast in BOTH themes.

## Source contract, not image-derived wiring

The initial named source snapshot is main
`155e130ea402f78a86558fb3c2b094c536be41a4`. Inspect the actual
[top-level routing](../../src/project.v), not text or arrows in generated art.
If source changes, rebuild/validate the dataset and label old results historical;
never carry current PASS forward solely because a screenshot looks unchanged.

| Source -> destination | Actual relation |
|---|---|
| Public `uio_in` -> input synchronizer | `async_in[7:0]`; runtime raw input, also shared with loader pins |
| Input synchronizer -> engine | `sampled_inputs[7:0]` from `sampled_in`; synchronized input, not raw input |
| Program store -> engine | `instruction[31:0]`, `instruction_valid` |
| Engine -> program store | `pc[4:0]`; bounded fetch, no implicit wrap |
| Data store -> engine | `tx_payload[7:0]`, `tx_payload_alt[7:0]` |
| Engine -> data store | `shift_result_data[7:0]`, `shift_result_write`; capture is not frame acceptance |
| Engine -> runtime pin routing | `gpio_value[7:0]`, `gpio_oe[7:0]` to `uio_out/uio_oe` outside load mode |
| Public loader -> program/data stores | Shared `uio_in` data and top-level selection/write/address controls |

There is no data-store-to-synchronizer dependency. Raw runtime inputs must not
be depicted as passing through program storage. `uo_out` is status or runtime
register readback, not an unconditional GPIO output bank. Loader ownership and
runtime ownership must be named separately.

The [program store](../../src/m1_program_store.v) is writable through public
pins, not ROM. The current source declares eight 32-bit words plus four length
bits and one ready bit. The [engine](../../src/m1_engine.v) declares 108
sequential state bits: PC/state 7, WAIT/input-wait 22, LOOP 19, SHIFT 44 and
GPIO value/direction 16. The [data store](../../src/m1_data_store.v) declares
25 bits; the [two-stage synchronizer](../../src/m1_input_sync.v) declares 16.
The derived sum is 261 + 108 + 25 + 16 = 410 declared state bits. This is
CHIP_COMPLETE state attribution, not mapped area or a final memory-depth choice.

Use RUN, WAIT, HALT and FAULT, not an invented IDLE state. WAIT counts accepted
edges; WAIT_PIN matches a synchronized LEVEL, not an edge detector. Reset is
synchronous and wins over enable. The engine reset predicate is
`engine_rst_n = rst_n && program_ready && !load_mode`. Disable freezes engine
state, but the input synchronizer remains clocked. HALT/FAULT are sticky until
reset. See the [execution](m1-execution-contract.md),
[loader](m1-program-loader.md), [input wait](m1-input-wait.md) and
[runtime readback](m1-runtime-readback.md) contracts for the actual behavior.

## Sparing relationship tracing

Tracing is guided navigation through proven source relationships, NOT simulated
signal activity. The representative path is input synchronizer -> engine via
`sampled_inputs[7:0]`. Name its source, destination and data/control role.

Prefer inverse emphasis: the chosen path and incident components stay clear;
unrelated connection STROKES in that local region gently decrease opacity
(proposed 0.6). Labels, source/evidence context and controls retain full contrast.
Do not dim the whole canvas or every component on each incidental hover.
Optional incident-region shading is achromatic light gray, never a tinted wash.

| Event | Required observable result |
|---|---|
| Intentional pointer dwell on an eligible relation | Show transient trace after about 150ms; do not override pinned or keyboard-origin trace |
| Keyboard focus on an eligible relation/list entry | Same trace and textual summary immediately; preserve focus outline |
| Tap, Enter or Space on that relation | Pin the trace and announce Selected relationship/pinned state |
| Pointer exit | Clear pointer-origin transient trace promptly (about 100ms); do not erase a pin or keyboard trace |
| Focus leaves the eligible relationship | Clear its transient trace unless pinned |
| Escape or Clear trace | Clear pinned/transient emphasis and restore normal view; retain usable focus |
| A new eligible event after clearing | May start a new trace; clearing must not immediately retrigger itself |

Pointer motion must not erase an intentional keyboard/pinned selection. Make
every thin graph edge reachable through a labelled outline/list alternative;
do not depend on pointer precision. Trace only source-backed edges and actual
directions, never inferred packets or undocumented cross-module paths.

At most one subtle directional travel cue may run once (proposed 600ms) when
useful. No perpetual particles, blinking, glow or fabricated changing values.
With reduced motion, retain the same static path, shading and text with no
travel cue. Cycle-model playback has separate explicit controls/state and never
starts from relationship hover. A static concept is not a tested animation.

## Exact initial cycle specimen

Use decoded SET(mask=01, value=01, oe=01), WAIT(1), HALT, with words
`0x00010101`, `0x40000001`, `0x80000000`. This reference scenario assumes a
committed program and released engine reset before execution. Reset model
resets reference execution, not a device or public-pin loader.

| State after edge | Reset model | Edge 1 | Edge 2 | Edge 3 | Edge 4 |
|---|---|---|---|---|---|
| `pc[4:0]` | 0 | 1 | 1 | 2 | 2 |
| State | RUN | RUN | WAIT | RUN | HALT |
| `wait_left[15:0]` | 0 | 0 | 1 | 0 | 0 |
| `gpio_value[0]` | 0 | 1 | 1 | 1 | 1 |
| `gpio_oe[0]` | 0 | 1 | 1 | 1 | 1 |

WAIT(1) consumes Edge 3; HALT executes Edge 4. Disabled edges freeze engine
execution; reset still wins. Align any reference strips to these exact columns,
retain full bus widths and offer the same data as an accessible table. No
invented intermediate clock pulses. If converting cycles to time, show the
declared assumption: 20ns at the 50MHz TARGET is not measured chip timing.

## Evidence and progress semantics

Follow the [evaluation contract](../research/evaluation-contract.md): status,
value provenance, workload and verification rung are separate fields. Display
the producing source hash/tool/run and caveat for every recorded result.
Missing, stale, branch-only and changed-source evidence never becomes current
PASS by inference. Offer an explicit neutral reason and original evidence link.

Keep [M0 physical evidence](../../evidence/E0010-pinned-cmos5l-run/README.md)
as an ARCHIVED GPIO baseline, distinct from current M1. M1 RTL/scoped formal
results are not M1 physical closure, full UART liveness or silicon evidence.
[UART TX](../../evidence/E0016-uart-tx-8n1/README.md) and
[bounded last-byte RX](../../evidence/E0018-uart-rx-public/README.md) qualify
their named digital workloads only. Raw-valid means capture, not acceptance;
bounded last-byte RX delivers only the last byte after both frames validate.

[PR8](https://github.com/KG-khangelani/protocol-emulator-asic/pull/8) is a
separate draft host-service candidate, NOT MERGED at this contract's date.
Its external host cache must not be counted as on-chip storage or silently
treated as main. SPI, I2C, compiler, M1 physical closure and silicon remain open.
M0 owner teach-back stays PENDING; engineering work never promotes fluency.
H1-H4 remain UNPROVEN. Do not publish a readiness/completion percentage.

## Approval and verification obligations

Explicit owner approval on 2026-10-05 opens visualization implementation,
including dark mode and softer/fewer boundaries. It does not approve PR8 merging.
The initial documentation checkpoint added no frontend/extractor/device driver;
the subsequent candidate adds a browser UI and a deterministic source exporter,
never a device driver. Publish cohesive reviewable documentation/code increments on a project
branch; do not hold every useful change until an entire milestone is complete.
Commit/push permission is distinct from merge, hardware-spend and submission
permission. Private assets, secrets and generated bulk remain out of Git.

Before claiming the future app implemented, verify:

1. Versioned source dataset, module/port widths, state accounting and evidence
   hashes match; changed/missing/stale/branch data fails closed without false PASS.
2. Reference stepping, WAIT boundaries, reset/disable, HALT/FAULT and malformed
   programs agree with independent expectations; retain failing seeds.
3. Search/selection/outline/layers/zoom/fit/details/copy and trace pin/clear work;
   shared URLs/refresh/back restore the same selected state and textual caveats.
4. Hover, keyboard focus and tap expose the same relationships; exit restores
   emphasis, pinned selection survives incidental motion, reduced motion is
   static, and tracing never starts cycle playback or implies activity.
5. Both light/dark themes and desktop/mobile portrait/landscape have readable labels, contrast, usable
   hit areas, native scroll and no clipped primary content. Inspect actual
   browser screenshots against the approved concepts, not build success alone.

At the initial documentation checkpoint all five app obligations were **NOT
RUN / NOT IMPLEMENTED**. The first working slice now has scoped local build,
source/model and real Chromium checks in [UI0001](../../evidence/UI0001-protocol-atlas/README.md).
The second bounded increment records 16 source/reference tests, 13 Chromium
cases, an independent JS/Python oracle, bounded cycle URL restoration, mobile
disclosures and fresh concept/render inspection. It uses `.\tools\atlas.ps1`
for a loopback-only Windows launch and adds a pinned frontend CI workflow.
The 256-row UI history bound is not an engine timeout. Browser checks do not
assert a full screen-reader audit or Safari/Firefox/iOS qualification.
That record does not assert complete coverage of every obligation. Existing
repository checks alone do not satisfy them or create new hardware evidence.
