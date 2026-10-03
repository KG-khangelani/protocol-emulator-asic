# D10 - Replace preload with a public-pin program store

Date: 2026-10-03. Status: experimental candidate.

Decision: replace the D9 constant preload with eight 32-bit writable words,
clock-synchronous byte writes, length commit, byte/length readback, and bounded
fetch validity. Loader controls use `ui_in`; program data shares `uio_in/out`.
Entering load mode resets execution, and a valid committed image begins at word
zero when load mode is released.

Reason: this is the smallest direct step that tests actual post-reset
reprogrammability rather than changing a testbench deposit or RTL constant. The
eight-word depth bounds state and exposes storage cost before protocol work.

Consequences: `P-RELOAD` now has RTL-simulation evidence for two observably
different programs loaded and read through public pins. The synchronous loader
assumes external setup/hold to the project clock; it is not an asynchronous
protocol or CDC result. Generic synthesis maps the flip-flop store very
expensively, so storage architecture is an explicit optimization question.
No new CMOS5L fit, timing, gate-level, or silicon claim follows.

