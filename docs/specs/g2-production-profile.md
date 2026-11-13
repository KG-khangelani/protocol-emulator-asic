# Qualified G2 production profile

D48 selects `od128-sram`, identified by runtime register 7 as **0x22**.
`tools/production-profile.json` binds the actual five RTL files, all twenty
physical input files, two vendor digital models and the complete qualification
records. `python tools/production_sram.py` verifies that identity; it does not
run new simulations or manufacture a new chip.

The instruction contract is the general engine described in
[D37's candidate contract](g2-general-io-candidate.md), with
[D42's SRAM/readback revision](g2-sram-prefetch-screen.md). The chip exposes
128 logical 32-bit words in a 256-by-32 physical macro. Program-bank register
5 selects eight-word banks 0..15; valid committed lengths are 1..128. Selecting
a bank invalidates the current image, and committing a valid length restores
bank zero. Invalid banks, lengths, partial programs and out-of-range fetches
follow the frozen fail-closed rules.

For program-byte readback, present a stable bank/address before a rising clock
edge and sample the returned byte after that edge. Reads work with either
enable value. Writes require reset released and enable asserted; reset wins
over writes and invalidates all logical words. Unwritten words read as zero.
Control/data register reads remain combinational. Runtime selector 6 exposes
the complete eight-bit PC; ordinary status retains its existing low-five-bit
PC field. The word-zero shadow preserves first-instruction timing after load.

Normal `make doctor check lint test test-verilator formal synth evidence`
commands select the actual `src/` files. Both simulators run the complete
thirty-group current suite. Formal verification includes source-matched
engine/store/prefetch properties, checked counterexamples and the independent
historical baseline. Generic synthesis reports the macro separately from
register state. The harness waveform is RTL smoke evidence.

The default manual `gds` workflow verifies production identity before staging
and requires regenerated physical inputs to match those files exactly. The
experimental `gds-sram` workflow remains separate; `gds-g1` retains the original
P/compact10 comparison. All three retain pinned tools and their stated gates.

Workload boundaries remain [UART TX](p-uart-tx-8n1.md),
[bounded UART RX](p-uart-rx-8n1.md), [four-mode SPI](p-spi-host-4mode.md) and
[Standard-mode I2C](p-i2c-controller-100k.md), together with D19's bounded host
service. The shared engine adds no dedicated UART/SPI/I2C hardware path.
The public clock's 50 MHz setting is the qualified flow target, not measured
Fmax. G3's assembler and user-facing program toolchain remain separately ordered.
