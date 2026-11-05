# D25 - Qualify a declared pin envelope and retain the full-proof limit

Date: 2026-11-03. Status: partial experimental digital qualification.

An instruction-level result becomes useful protocol evidence only when its
program produces the right external clock, selection and data timing. Extend
D24 with independent pin mathematics and the actual public-loaded eight-word
compact image. Preserve production/candidate RTL and existing source hashes.
The [pin contract](../specs/spi-mode0-pin-qualification.md) fixes the schedule,
timing envelopes, synchronization model, acceptance and proof boundaries.

Keep two envelopes distinct. The original seed permits per-bit target response
5..480ns at the50MHz simulation target, giving at least20ns setup before SCK
rises. A separate ideal digital stress envelope holds the intended bit only
on R+-1ps and permits arbitrary transitions outside that window. This tests
sample alignment and sensitivity to irrelevant transitions; it cannot specify
electrical setup/hold, metastability, propagation delay or physical timing.

Try the actual compact top/program/data stores/synchronizer/executor in a
public-driver SAT proof through444 steps, with symbolic bytes/order and only
raw MISO constrained at the eight rising edges. Retain two tool-conversion
failures and the direct/reduced90-second solver timeouts. Neither whole-program
attempt passes. Do not shrink the result into an end-to-end formal claim.

Use a separate actual-synchronizer proof and independent schedule monitor for
the transport claim. Partial-byte invariants are assertions, not new input
assumptions; they exclude unreachable induction starting states. Keep its
initial UNKNOWN trace. Induction checks the written transport rules; covers
reach both order completions and changed outside-window input. An early
monitor must fail with a concrete witness. This proof contains no executor,
loader or firmware and cannot substitute for their full-program proof.

Use public-pin simulation for complete-program claims: image readback, every
GPIO edge, rising-edge wire decoding, exact result visibility and known-image
HALT acceptance. A delay0 SAMPLE plus one extra WAIT keeps SCK/CS unchanged yet
misreads late input; retain it as a firmware control, not a candidate defect.
Reject out-of-envelope response profiles even when unchanged all-one data
masks the violation. Reset/disable invalidate fixed-rate acceptance.

E0024 records successful scoped observations, negative controls, failures and
limits separately. Next, develop per-loop invariants or another measured
decomposition for the actual eight-word full-program proof before considering
production promotion. Keep PR11 draft/unmerged, PR8/compiler deferred, the
visualizer intact, H1-H4 unproven and M0 owner fluency PENDING.
