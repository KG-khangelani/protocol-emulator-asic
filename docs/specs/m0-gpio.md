# M0 GPIO behavioral specification

Status: implemented; **RTL regression passed in E0002**. This is a toolchain probe; it does
not establish any claim about a programmable protocol architecture.

Top: `tt_um_khangelani_protocol_emulator`. One clock domain. Initial timing
target: 50 MHz / 20 ns, matching the unchanged template `CLOCK_PERIOD`.

## State transition

The state is an unsigned 8-bit counter `q`. On each rising edge of `clk`:

| Sampled condition | State immediately after the edge |
|---|---|
| `rst_n = 0` | `q = 0`, regardless of enable |
| `rst_n = 1`, `ena = 1` | `(previous q + 1) mod 256` |
| `rst_n = 1`, `ena = 0` | Hold previous q |

`uo_out = q`; `uio_out = 0`; `uio_oe = 0` at all times. `ui_in` and `uio_in`
are ignored. Reset is **synchronous**, active low. Apply reset through at least
one rising edge before observing state; power-up values are not specified.
Changes to reset or enable between rising edges must not change state.
Enable preserves phase while paused; re-enable continues counting.

| Enabled edge since reset | 0 (reset sampled) | 1 | 2 | 3 | 254 | 255 | 256 | 257 |
|---|---|---|---|---|---|---|---|---|
| `uo_out` hex | 00 | 01 | 02 | 03 | FE | FF | 00 | 01 |

For continuous enabled operation, bit `i` toggles every `2^i` active edges and
has period `2^(i+1)` clock cycles. Electrical delays are outside this RTL model.

## Verification contract

1. Reset from nonzero state with enable both low and high.
2. At least two complete counter wraps with pin-level expected values.
3. Pause and resume without phase loss.
4. Seeded random enable, sampled reset and ignored-input changes.
5. Between-edge input/control perturbations cannot alter observed output.
6. All bidirectional output enables remain deasserted.

The cocotb oracle counts accepted edges independently and observes public pins,
so the same harness can exercise the generated gate-level netlist. It samples
1 ns after rising edges in zero-delay functional simulation. This is not a
post-layout SDF or analog glitch/metastability assessment.
