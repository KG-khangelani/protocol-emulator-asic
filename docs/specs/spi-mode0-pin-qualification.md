# Compact eight-word mode-0 pin qualification

Status: isolated digital experiment, 2026-11-03. Baseline PR11
`0b0409ea4078a997a0a487f36ebfac286d5d46a7`. Production and candidate RTL
remain unchanged. This extends E0023 to the actual eight-word SPI program;
it does not promote four-mode SPI, physical timing or production readiness.

## Independent schedule and successful-transaction assumptions

Use the eight literal words from the compact image in
`spi-phase-comparison.md`, with order encoded in the DRIVE/SAMPLE words.
Load through public pins, commit length8 and write TX. Simulation also reads
back all32 bytes. Leave loader mode and flush the synchronizer for two disabled
edges with idle MISO1. The target is detached during loading/readback. Resolve
released CS high and SCK/MOSI low; GPIO1/MISO remains an input throughout.

Successful execution has no reset, reload or disabled edge. Core period is
20,000ps, a simulation target rather than measured silicon timing. For j0..7:
low/DRIVE L=2+50j; rising R=27+50j; capture C=R+2. SCK high and inter-bit low
intervals are25 core periods. CS asserts at2, releases with final falling edge
402, and HALT is403 atPC7. MOSI changes at L and stays stable through R and the
high phase. CS setup/last-rising hold and MOSI setup are25 periods. Expected
GPIO, edge lists and wire-decoded bytes come from pin mathematics, without
decoding instructions or reading executor state.

The original seed envelope launches bitj after L with response5..480ns,
independently variable per bit, and holds until the next launch (last bit
through CS release). That guarantees at least20ns input setup before R.

A separate digital stress envelope requires the intended MISO bit on the
closed window [R-1ps,R+1ps]; transitions outside those windows may be arbitrary.
This tests dependence on the correct sampled edge, including glitches outside
the aperture. It is not an electrical setup/hold specification: the model uses
ideal flip-flops without metastability, propagation delay, jitter or analog
contention. Raw transitions requested exactly on a core edge move1ps before
that edge, as declared deterministic simulation ordering. Record actual times.

## Formal boundary

Try a bounded proof of the actual uninstrumented compact top and all five
runtime modules. The public driver resets once, serializes32 program bytes,
commits8, writes symbolic TX and flushes twice. Symbolic RX/order remain constant
for the transaction. MISO is otherwise arbitrary at every formal core tick;
only its value at each R is constrained to that bit. Runtime raw/valid read
selection varies freely. No memory preload, internal force, abstract fetch,
engine readout or assumed result pulse is permitted.

Driver cycles0 reset,1..32 byte writes,33 length,34 TX,35..36 flush,
37..439 execution1..403,440 status read,441 chip reset,442 cleared-state check.
Check every public GPIO edge, release of RX, exact raw/valid visibility from
capture379, HALT/status and reset. Configured SAT bound444 includes the final
check; no induction or arbitrary-program liveness follows. Digital formal ticks
do not represent sub-cycle transitions; simulation checks those separately.
No initial-zero shortcut or unknown-cell ignoring is allowed. Any timeout or
unsupported tool is inconclusive, never PASS. E0023's earlier guided abort
timeout remains inconclusive and is not overwritten by this experiment.

The direct444-step SAT attempt and its Boolean-reduced retry both exceeded
the90-second solver budget. Retain their exact inputs, commands and logs as
INCONCLUSIVE. They supply no full-program formal qualification.

The required, smaller formal boundary uses the actual unmodified input
synchronizer and an independent schedule counter, without an executor/store.
Assume only the intended bit at each R; other sampled MISO ticks are arbitrary.
Prove the two-stage recurrence, consumption of that bit at C=R+2, and a monitor
byte assembled from those eight observations. Configured induction depth8;
cover depth404 must reach both orders' complete0x69 and a changed outside-window
input. An early C=R+1 monitor mutant must fail within BMC32 with a witness.
This proves input transport under the digital aperture assumption, not the
eight-word firmware or loader. Complete-program claims rely on simulation
and retain the existing E0022/E0023 property boundaries.

## Simulation and falsification obligations

On both simulators run the public-loaded full byte alphabet in both orders at
the latest stress launch; sweep all original quarter-clock responses and
per-bit jitter/noise corners. Check every execution edge, independent actual
SCK rising-edge MOSI/MISO decoding, capture before CS release and acceptance
only after known-image HALT. Preserve small representative timestamped traces
and an explicit case manifest, not bulk simulator waveforms.

A firmware control moves SAMPLE one edge earlier (delay0) and adds one WAIT
edge afterwards, keeping external SCK/CS identical. Under late digital input,
require a received-byte mismatch against the rising-edge wire oracle; this is
a deliberate program mutant, not a candidate RTL defect. Also reject an
out-of-envelope input trace and fixed-rate acceptance after reset/disable.
Keep intended target byte, wire-observed byte, raw-valid and accepted result
distinct. All-ones masking must not turn a timing violation into qualification.
Check both actual window values and declared response deadlines; an unchanged
all-one wire can satisfy the former while its declared launch violates the latter.

Record commands, source hashes, assumptions, actual proof bound/outcome,
positive case counts and negative witnesses. Keep PR11 draft/unmerged,
PR8/compiler deferred and owner-learning status independent.
