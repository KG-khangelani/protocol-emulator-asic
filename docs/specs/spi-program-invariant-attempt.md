# One bounded actual-program invariant attempt

Status: proposed experiment, 2026-11-03. Baseline PR11
`4e207793b6cc7fb6602c4e8ee43775be4e9c28e7`. E0024's two full-program solver
timeouts and all counterexamples remain unchanged and inconclusive.

## Same claim and subject

Keep E0024's exact public driver and eight encoded words. Compile the actual
compact top, full program/data stores, executor and input synchronizer. Reset
once, serialize32 bytes, commit8, write symbolic TX, flush twice and execute
403 continuously enabled edges. RX and order are symbolic constants; raw MISO
and runtime raw/valid selection remain arbitrary each tick. Only MISO at
R=27+50j is constrained to the intended bit, exactly as in E0024. No new input
assumption, internal preload, substituted fetch, forced ready or monitor-only
replacement is allowed. Digital sampled ticks retain E0024's ideal model;
no electrical timing, other SPI mode or production-readiness claim follows.

Check the original public GPIO, raw/valid, HALT and reset assertions. Add
read-only taps with checked inverse transforms. They expose actual state to
assertions; they add no DUT input or state and do not constrain it by assumption.

## Proposed strengthening assertions

At every prefix tick assert all actual program bytes equal the bytes already
written through the public loader, with unwritten/reset bytes zero. Check
length/ready and TX/RX register lifetimes against that public sequence.

For each real loop iteration assert PC, Run/WAIT state, remaining wait, loop
count/targets, phase flags, shift count/configuration and partial TX/RX state.
The phase table is stated in completed accepted edges n. In bitj's body,
L=2+50j and t=n-L:

| t | PC | State | wait_left | phase condition |
|---|---:|---|---:|---|
|0|2|Run|0|bit driven/prepared|
|1..23|2|WAIT|24-t|ordinary low wait|
|24|3|Run|0|ready to raise SCK|
|25|4|Run|0|SCK high|
|26|4|WAIT|1|delayed SAMPLE pending|
|27|5|Run|0|sample committed to partial byte|
|28..48|5|WAIT|49-t|ordinary high wait|
|49|1, or6 after final bit|Run|0|loop count advanced|

Loop target is6 and start1. At n402 release CS/fall SCK and advance toPC7;
n403 HALTs. RX commit is edge379. Assert these actual values, including each
partial receive prefix; do not assume them. Tie synchronizer taps to previous
public uio values and assert the consumed bit at each capture R+2.

## Budget, validation and stopping rule

First run finite simulation preflight of the actual instrumented top plus
these assertions, with concrete bytes/orders. Replace formal assumptions by
assertions in the simulation-derived driver so that its witness also checks
the timing premises. This is harness validation and a finite witness, not proof.
Only repair demonstrated harness mistakes before freezing the attempt.

Then run **one** SymbiYosys/Z3 prove job, configured induction depth12 and a
180-second subprocess wall limit. Preserve PASS, FAIL, UNKNOWN or timeout as
returned. Do not retry another proof configuration or increase the budget in
this experiment. A successful k-induction proves the written actual-program
properties under the fixed driver/premises, including its quiescent tail; a
base-only pass is only bounded evidence, and UNKNOWN/timeout is inconclusive.
No full444-step BMC or formal reachability cover is promised. Simulation
witnesses are labelled separately and cannot turn an inconclusive job green.

If published, CI runs this same configuration with the same limit and retains
the raw result. Keep the PR draft/unmerged, production/candidate RTL and
PR8/compiler deferrals unchanged, and owner-learning status independent.
