# E0034 - Receive SDA using the existing shift operation and SCL falling edge

Date: 2026-11-12. Goal: G2, following D36/E0033. **Scoped receive kernel PASS;
full I2C remains unqualified.** All five generated RTL files match D35's
qualified compact10 candidate. There is no RTL change.

The nine-word public-loaded program repeats WAIT, release SCL, WAIT_PIN,
high-period WAIT and SHIFT_STEP eight times. With TX payload zero, SHIFT_STEP
pulls SCL low while sampling synchronized SDA on its distinct receive pin.
This reuses the existing operation without actively driving either bus line
high. It needs no dedicated receive instruction or protocol hardware.

Icarus and Verilator each pass one group and produce 268 identical records:
264 positives and four expected rejections. The positives cover all 256 byte
values and stretching at each of the eight clock releases. Target responses
use four offsets (4, 5, 690 and 7 five-nanosecond ticks); these cover all four
core-clock phases, with one assigned offset per byte, not a full cross product.
Stretch controls use the maximum unstretched data-valid delay of 690 ticks.
The target reacts only to public SCL transitions and drive releases.

Each image is loaded and read back through the banked public loader. Only the
first case resets the chip. Subsequent cases reload and invalidate raw-valid
through a public payload write; the previous raw byte remains until the eighth
capture. Runtime selectors observe raw data and validity without taking bus
ownership. No hierarchical executor handles are used.

Unstretched SCL is **98,619.329 Hz**, not exactly 100 kHz: the normal cycle is
1,048 low plus 980 high ticks (5,240 + 4,900 ns). The first low is 1,052 ticks.
The measured overhead is retained. This kernel omits address, ACK/NACK,
START/STOP, terminal outcome markers and timeout cleanup; no complete I2C
transaction is accepted from it.

| Negative control | Observable rejection |
|---|---|
| Nonzero TX (0x80) | Active-high SCL, incorrect clock count/wire/result |
| LSB-first capture of MSB-first 0x69 | Wrong raw byte despite correct wire timing |
| Zero high WAIT | High width and maximum frequency violations |
| Permanent stretch on fourth release | FAULT mid-byte, no fresh completed result |

`experiments/i2c/public_bus.py` uses the simulator's native 20 ns clock and
wakes Python on public changes or target events. Runtime selectors are polled
at those observations. For these kernels, every capture coincides with a
visible SCL transition; the independent checker verifies the result and valid
transition at the eighth falling edge. The transport is not a universal monitor
for a program that changes raw data without a public wake-up event. Its 5 ns
event model establishes no analog pad, RC, spike-filter or MTBF guarantee.

## Reproduce

Inside the locked workbench:

```sh
python3 experiments/i2c/run_receive.py --output build/i2c-receive/new-attempt
```

Use a new output directory. `result.json` records exact source hashes, commands,
actual simulator identities and equality checks. Both simulator folders retain
logs, JUnit, all case records and selected full public traces, including every
negative. `development.json` retains an initial runner SyntaxError and its
correction. Curated checksums cover this evidence; elapsed times are observations,
not deterministic reproduction requirements.

Next compare complete schedules using general conditional timeout branching
and larger storage, with and without a general open-drain serial-output option.
Measure the word counts, independent-oracle behavior and complete-chip cost
before selection. The existing receive operation is a useful baseline; no
combined protocol, formal, fresh physical or owner-fluency promotion follows.
