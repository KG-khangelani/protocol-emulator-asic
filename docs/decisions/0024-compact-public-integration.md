# D24 - Qualify the actual public integration before protocol promotion

Date: 2026-11-03. Status: bounded experimental integration qualification.

An executor can compute the right byte while the surrounding chip loses it,
loads the wrong instruction or mishandles an interruption. Extend D23 to the
actual compact-copy top, eight-word program store, data registers and two-stage
synchronizer. Keep production RTL and the uninstrumented candidate unchanged.
The [integration contract](../specs/spi-phase-integration.md) fixes the boundary,
public stimulus, lifetimes and proof limits; E0023 retains inspectable evidence.

Prove universal written safety assuming only sampled chip reset initially.
Expose existing program/synchronizer/phase state through read-only wires, with
checked inverse transforms. Reuse executor assertions as an observer of the
connected instance, removing its standalone reset assumption and covers. Use
the real loader and all 256 program bits: do not stub ready, fetch or capture.

Separately drive a real serialized four-word LOOP/DRIVE/SAMPLE/HALT image at
public pins. Symbolic TX/RX bytes and order check complete capture and readout.
The guided formal abort is the final capture edge41, with symbolic loader-read,
program-write or chip-reset and enable0/1. Broader symbolic cut2..41 exceeded
the 300-second budget and is retained as a timeout, not a pass. Universal safety
still admits arbitrary abort timing; dual-simulator tests cover all40 cuts.

Keep documented lifetimes precise. Entering loader mode resets execution even
with enable0 and blocks a simultaneous completion. It preserves an older
completed RX byte and valid flag. Payload writes invalidate valid but retain
raw RX; chip reset clears all storage. A selected loader read drives the public
bus even during reset; reset clears engine GPIO without overriding that mux.
These are existing behaviors, not newly discovered candidate defects.

Require falsification witnesses for an intentionally wrong loader-clears-valid
claim and a disconnected result-store write mutant. Preserve the initial test
fixture failure: its runtime-read helper was called while still in loader mux
mode; moving the observation after runtime selection/flush repairs the fixture.
Neither deliberate failure nor fixture correction justifies a candidate change.

Induction establishes written safety; the public-loaded completion and abort
jobs establish only their finite schedules. Neither proves complete SPI modes,
arbitrary-program termination, electrical timing or physical readiness. Next,
qualify the eight-word mode-0 program end to end with explicit external-pin
timing assumptions. Keep PR11 draft/unmerged, PR8/compiler deferred, H1-H4
unproven and owner M0 fluency PENDING.
