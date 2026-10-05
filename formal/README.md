# Formal verification

The active `make formal` target checks the M1 engine. Historical M0 proof files
and retained E0007 evidence remain available and are not rewritten.

## M1 active suite

`m1_engine_formal.sv` proves sampled reset priority, enable and terminal-state
stability, exact WAIT decrement/completion, SET masking, opcode validity, PC
behavior, LOOP transitions, SHIFT_STEP progression/result assembly, and safe
HALT/FAULT outcomes. It also proves arbitrary legal-period SHIFT_BURST
countdown, bit transitions, final hold, payload-slot toggling, reset and enable
freeze. Covers reach WAIT(2), HALT, FAULT, the seventh shift step, same-edge
shift completion, timed completion and use of both payload slots.
The mutation job deliberately demands an incorrect decrement-by-two result and
must find a counterexample. These properties cover the reusable executor input;
they do not prove physical timing.

`m1_program_store_formal.sv` separately proves reset clearing, valid and invalid
length commits, write invalidation, selected-byte readback, and fetch validity
bounds. Covers reach a ready eight-word image and an unready empty image. The
end-to-end public-pin reload sequence remains a simulation property because the
engine and store proofs are compositional, not one combined liveness proof.

`m1_data_store_formal.sv` separately proves reset clearing, both TX-payload writes,
RX-result capture, RX-valid invalidation, retained state, and exact readback for
implemented and reserved addresses. Its result-capture input is constrained by
the engine only in top-level simulation; the proof checks the store for every
possible input value and timing.

`m1_public_readout.sby` proves combinational public status/register decode,
GPIO/loader ownership and load/reset selection against arbitrary top-level
inputs and state. It does not prove integrated receive liveness; public-pin
simulation supplies that check. No extra retained state is added by readout.

## Archived M0 suite

Formal verification turns the transition table in
`docs/specs/m0-gpio.md` into mathematical statements. Instead of choosing a
finite list of inputs, the solver searches all allowed reset, enable, state,
and ignored-input values for a counterexample.

Run it from Windows with:

```powershell
.\tools\workbench.ps1 Formal
```

The command performs three related checks:

| Check | Purpose | Required result |
|---|---|---|
| `prove` | Prove reset priority, increment, hold, wrap, fixed bidirectional outputs, and ignored-input independence | PASS |
| `cover` | Produce concrete reset-to-`FF` and `FF`-to-`00` traces | PASS |
| `mutant` | Run the same assertions against an intentionally wrong increment-by-two implementation | Expected FAIL found by step 2 |

## Why there are two DUT copies

`m0_gpio_formal.sv` instantiates the design twice. Both copies receive the same
clock, reset, and enable, but receive independent `ui_in` and `uio_in` values.
Once a reset has been sampled, their public outputs must remain equal. This is
a direct check that the inputs specified as ignored cannot influence behavior.

The safety proof has no input assumptions. Power-up counter state remains
unspecified, matching the RTL specification; comparisons between the two
copies begin only after a shared sampled reset. The cover-only build assumes a
single reset followed by continuous enable so it can produce a short, readable
wrap witness without exploring irrelevant pause/reset combinations. That
cover assumption is not compiled into the proof.

## What a pass means

The current RTL satisfies the written digital properties under the formal
model, and the cover traces demonstrate that the wrap states are reachable.
The rejected mutant is a falsification check: it shows the assertions are able
to detect at least one plausible implementation error rather than passing
vacuously.

The result is still bounded by the properties we wrote. It does not model
analog delay, metastability, power-up circuitry, post-layout timing, or
fabricated silicon. Those questions belong to other stages in the project map.
Raw proof, witness, and counterexample files are generated under ignored
`build/formal/`.

## Bounded external host arithmetic (E0019)

`uart_rx_host_deadline.smt2` is a QF_LIA integer lemma, not an RTL harness.
`tools/check_host_deadline.py` requires UNSAT for the negation of first-copy
safety under H+L<=10P, followed by SAT for a deliberately one-edge-weakened
bound. `make formal` runs it after all existing RTL proof/cover/mutation jobs.
It assumes settled post-edge polling, integer H/L/d and the separately tested
10P raw-capture spacing. It proves neither integrated RX liveness nor
asynchronous service, pad access time, analog baud tolerance or physical timing.
