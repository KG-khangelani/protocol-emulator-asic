# E0027 - Four-mode timing and program-capacity screen

Observed2026-11-11 UTC /2026-11-12 Johannesburg, baseline f9dcd8a.
The four-mode timing contract and independent oracle are now executable.
**A delayed SAMPLE saves one instruction under an explicit held-input contract.**
Production and experimental candidate RTL are unchanged.

## What ran

| Boundary | Result |
|---|---|
| Independent edge/boundary/mutation tests | Seven PASS |
| Instruction-reference positive cases | 6,176 PASS across all modes/orders and the byte alphabet |
| Reference controls | Sixteen checked, including held-data/edge-only and naive-boundary cases |
| Icarus public-loaded screen | 36 cases:26 accepted and10 correctly rejected |
| Verilator public-loaded screen | Same36; complete public records byte-identical |
| New synthesis, physical flow, full four-mode RTL qualification | NOT_EVALUATED |

The actual RTL screen includes24 new held-data successes: modes0/2, both
orders and six payloads each. Four edge-only cases reject that optimization.
Eight naive-image controls add two mode0 successes and six boundary failures.
The6,176-case alphabet sweep is a reference-model result, not an RTL count.

## Word saving and its price

The [contract](../../docs/specs/p-spi-host-4mode.md) freezes fixed board pulls,
idle clock before selection, H=25 CS setup/hold and1MHz target SCK. It preserves
the mode0 comparison margins. Microchip supplies the mode edge conventions;
the margins are this project's digital test conditions.

| Examined schedule | Modes0/2 | Modes1/3 | Input requirement |
|---|---:|---:|---|
| Exact capture plus explicit preamble | 9 words | 11 words | Intended bit at wire sample S |
| Delayed capture absorbing final WAIT | 8 words | 10 words | Intended bit also at S+22 |
| Naive old eight-word image with changed clock values | 8 words | 8 words | Boundary contract fails for modes1/2/3 |

The existing exact mode0 image still works in8 words with fixed low SCK pull;
the9-word exact row includes the explicit preamble used for both polarities.
This is a comparison of declared families, not a minimum-word proof.

Delayed SAMPLE captures at S+24 and consumes synchronized raw S+22.
The original held-response envelope guarantees that value. E0025's edge-only
premise does not: with wire RX0x69 and opposite values away from S, the delayed
image returns0x96. Both simulators reproduce that expected rejection.
No E0025 proof is extended to this new firmware by implication.

The saved word makes room to establish idle clock with CS high. Modes0/2
then fit and publicly load in the existing eight-word compact candidate.
Modes1/3 need two more words in the examined held-data schedule because
clock initialization, CS assertion and setup delay must precede the loop.
The10-word compact-encoding reference is not the earlier plain-encoding banked
candidate; no existing banked area figure qualifies this unimplemented combination.

## A boundary failure that a correct byte hides

The naive mode2 image returns the expected0x69 but raises SCK to its idle level
on the same edge it asserts CS. The fixed board was previously pulling SCK low.
The oracle rejects that idle-before-CS violation, on both simulators.
Naive phase1 images also miss the declared leading-edge/setup schedule.

The new mode2 held image establishes SCK while CS is high, asserts CS later,
and maintains the full25-clock setup. All observations use public loading,
readback, GPIO, raw/valid and status. No private DUT handles or oversized
reference program are used for an RTL success.

## Reproduction and evidence

Inside the locked container:

    python3 experiments/spi_phase/run_four_mode_screen.py --output build/spi-four-mode-screen/new

The reference-only executor explicitly permits16 words. Every model result
reports actual capacity8, word count, fit status and RTL NOT_EVALUATED.
Only fitting eight-word images enter the separate public RTL tests.

[run-result.json](run-result.json) retains commands, source hashes, results
and simulator-record hashes. [schedule-matrix.json](schedule-matrix.json) records
encoded words, capacity and scoped outcomes. Generated compact RTL, JUnit,
logs, all public case summaries and compressed representative traces are
retained. Deterministic gzip preserves original trace bytes; only recorded
log whitespace/line-ending normalization is applied.

This is a core-tick digital screen: raw values are applied1ps before their
sampling clock edge. It is not metastability, sub-cycle-noise, device electrical,
arbitrary-firmware or full four-mode qualification. Six RTL payloads per new
mode/order do not establish exhaustive data coverage.

Next prove the fitting delayed-capture images under their actual input-hold
premise, and investigate phase1 schedule capacity without treating these
family counts as a global lower bound. See
[D28](../../docs/decisions/0028-delayed-sampling-under-explicit-hold.md).
