# Compact candidate public integration qualification

Status: proposed isolated experiment, 2026-11-03. Baseline PR11 head
`284c9cc6e6f6b5b70403a3ab2b704205eac3b861`. Production RTL stays unchanged.

## Actual boundary and assumptions

Compile the actual compact top, eight-word program store, data registers,
two-stage input synchronizer and executor. Do not substitute instructions,
ready, result pulses or storage. Formal-only readouts expose program bits,
synchronizer stage1 and phase flags; mechanically invert every readout change.
An observer checks the E0022 executor assertions on the actual connected state,
with its standalone assumption/covers removed. It does not instantiate a second
executor or constrain an internal signal.

The universal job assumes only chip reset on the first sampled edge. Every
subsequent public ui/uio input, enable and reset is symbolic. A symbolic constant
byte address selects one of all32 program bytes for a public-write scoreboard.
Check loader byte/length/readback/fetch decode, actual synchronized inputs,
same-edge result capture, payload-write priority, GPIO ownership and reset/abort.
No fairness, valid-image restriction, stable program or external protocol timing
is assumed. This is a digital single-clock model, not a contention or CDC proof.

Entering loader mode resets the executor even with ena0 and blocks capture on
that very edge. It preserves old completed RX data/valid unless a TX/alternate
payload is written. Payload writes clear valid but retain the raw RX byte.
Chip reset erases program, data and execution state regardless of enable.
Invalid length clears ready/length; program-byte writes clear ready. Runtime
read selectors do not write or reset anything. These lifetimes follow existing
`k-shift-8.md` and loader/readback contracts; do not silently strengthen them.

## Publicly loaded bounded witness

The guided harness drives only public pins. It serializes a four-word
image: LOOP(length2,count8), DRIVE(TX0,RX1,order), SAMPLE(delay3), HALT. TX/RX bytes
and bit order are symbolic constants. No internal preload or forced fetch is
allowed. After byte writes, commit length4, write TX and provide two disabled
synchronizer flush edges. Loader readback is universally checked by the byte
scoreboard; simulation explicitly reads the complete image before executing it.

Accepted execution edges: LOOP1, DRIVE at2+5j, SAMPLE issue3+5j, capture6+5j,
for j0..7. Last capture41; HALT42 atPC3. Raw RX bitj is presented from DRIVE's
edge, so the real synchronizer supplies that bit at capture. Runtime RX read
selection stays active through execution; expected TX GPIO, RX release, result
visibility and terminal state come from the independent schedule/byte operands.
This is a generic byte-transfer kernel, not an SPI timing qualification.

Driver cycles0 reset;1..16 program-byte writes;17 length;18 TX;19..20 flush;
21..62 execution. Then read valid/status, enter loader read with ena0 (retain
completed RX), read again, write alternate TX (invalidate only), and chip-reset.
Assertions compare post-edge values against the previous driver cycle. Counts
are formal clock steps, with no physical frequency assertion.

The abort harness uses the same real load and fixes the execution cut to the
final capture edge41, with symbolic kind loader-read/program-write/chip-reset
and enable0/1 on that edge. Simulation covers all cuts2..41. The unrestricted
integration safety proof permits public reset/load changes at any clock.
After the cut it holds execution disabled and checks abort, no newly valid
partial byte and reset/readiness effects. It starts without an old valid byte;
the completion harness and universal retention properties cover old-data lifetime.

Reset clears logical engine GPIO. A selected loader read still owns/drives all
eight public uio pins, including during chip reset; runtime selection exposes
the cleared GPIO instead. This is existing mux behavior, not a tri-state or
electrical contention guarantee.

## Falsification and bounds

Try to falsify the tempting claim that loader entry always clears RX-valid:
the completion/loader-read path must produce a counterexample with old valid
data retained. This rejects an assumption, not the documented candidate.
A separate dropped result-store write connection mutant must fail after a real
public load/transfer; retain its concrete witness. No production fix follows
from deliberately wrong expectations or mutants.

Configured jobs: universal k-induction search depth8; guided completion
BMC/cover depth80; guided abort BMC/cover depth72; wrong-clear BMC80; dropped-write
BMC80. Completion has four covers and abort has four covers, including the last
capture edge and enable0 reset priority. Tool failure/UNKNOWN/timeout is not PASS.
Record actual induction/base/cover/failure steps and exact assumptions. Finite
guided results apply only to these schedules; they do not establish complete
SPI, arbitrary-program termination, physical timing or production readiness.
