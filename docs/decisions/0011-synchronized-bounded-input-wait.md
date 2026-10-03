# D11 - Synchronize inputs and bound event waits

Date: 2026-10-03. Status: implemented candidate; local qualification passed.

Decision: sample each `uio_in` bit through two clocked stages and add the
provisional `WAIT_PIN(pin, level, timeout)` instruction defined in
`../specs/m1-input-wait.md`. The synchronizer advances independently of engine
enable. The engine observes only its second stage on enabled execution edges.
Every unmatched wait has an explicit accepted-edge bound; expiry enters sticky
FAULT, and a match on the final eligible edge wins.

Reason: input-dependent protocols require a declared clock-domain boundary and
cannot wait forever. Keeping synchronization separate from engine enable avoids
turning a paused interpreter into a stale sampler. Terminal FAULT makes an
unmet environmental assumption visible rather than silently continuing.

Consequences: the first actionable observation is three rising edges after an
external level is stable before the first edge. This is a deterministic RTL
contract, not a metastability/MTBF result. It does not specify asynchronous edge
capture, open-drain electrical behavior, contention, or any protocol firmware.
`K-INPUT-WAIT` remains not fully evaluated because its workload requires a
protocol kernel and HALT-within-bound result; this candidate instead exercises
the primitive and reaches terminal FAULT on timeout.
