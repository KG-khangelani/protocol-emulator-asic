# Delayed SPI program proof under explicit input hold

Frozen attempt: 2026-11-12. Baseline 3927165. Subject: E0027's eight-word
HELD programs for modes 0 and 2, actual compact experimental RTL, public loader,
data/program stores and synchronizer. Production and candidate RTL remain unchanged.

TX and RX bytes, bit order and CPOL are symbolic constants. Thus one successful
induction covers both modes, both orders and all byte pairs under this driver.
Serialize all 32 program bytes, commit eight words, write TX and flush twice.
Execute 404 continuously enabled core edges, observe HALT, then reset. Runtime
raw/valid selection stays arbitrary. No internal preload or assumed state.

CS asserts at A=3. Launch D_j=3+50j, wire sample S_j=28+50j, trailing edge
T_j=53+50j, capture C_j=52+50j. CS releases at 403; HALT is 404.
SCK establishes CPOL with CS high at edge 1. MISO remains an input.

## Premise and scope

Constrain raw MISO to the intended bit only at core ticks S_j through T_j,
inclusive. HELD_RESPONSE implies this band: its latest response is D_j+24
and its earliest next response occurs after T_j. The last bit holds through
release. Ticks outside the band are arbitrary. This abstraction admits more
input traces than the electrical response envelope; it makes no analog claim.

The synchronizer consumes raw C_j-2 = S_j+22. Prove its transport and each
capture bit, then the partial byte, public result/valid timing, clock/CS/MOSI
waveform, output direction, HALT and reset. Keep the complete loaded-state
and execution-state invariants as assertions, never assumptions.

For n completed execution edges, bit j starts at L=3+50j, t=n-L:

| t | PC | State | wait_left | Meaning |
|---|---:|---|---:|---|
| 0 | 3 | Run | 0 | Drive bit and idle clock |
| 1..23 | 3 | Waiting | 24-t | First half-period wait |
| 24 | 4 | Run | 0 | Ready for sample edge |
| 25 | 5 | Run | 0 | Clock changed at S_j |
| 26..48 | 5 | Waiting | 49-t | Delayed capture pending |
| 49 | 2, or 6 after final bit | Run | 0 | Capture and loop advance |

The period register is a pending-capture marker (1), not the delay value.
First SET uses PC0; LOOP uses PC1, start2/end6. RX commits at edge402.

## Validation and fixed budgets

Before formal execution, simulate the instrumented assertions in Icarus with
concrete bytes, both modes/orders and early/late/jittered lawful core-tick inputs.
Convert assumptions to assertions, verify all eight serialized words against
the independently encoded E0027 image, and retain public traces. These finite
witnesses validate the harness and show terminal reachability; they are not a
formal reachability cover or exhaustive simulation.

Then run each configuration once with Z3 and a 180-second process-group limit:

| Case | Configuration | Required result |
|---|---|---|
| Held baseline | prove, depth12 | PASS with actual k-induction |
| Wrong MOSI goal at first drive edge3 | BMC, depth44 | Reachable FAIL at public GPIO assertion |
| Remove first post-sample hold, keep first wire sample and other bits | BMC, depth92 | Reachable FAIL at first delayed capture, showing incorrect synchronized bit |

Require the expected assertion location and trace values for both negative
controls. Timeout, missing status, tool failure or unvalidated counterexample
does not count as success. No increased budget or adaptive proof retries.
Repair only demonstrated preflight harness errors before freezing the attempt.
Retain unsuccessful attempts with their exact inputs.

No mode1/3 qualification, arbitrary firmware/pauses, new physical result,
Fmax, silicon, production promotion or owner fluency follows.
