# M0 formal verification

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
