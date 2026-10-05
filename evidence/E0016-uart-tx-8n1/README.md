# E0016 - Timed shift burst and digital UART-TX qualification

Question: can an eight-word public-pin program emit two independently chosen,
back-to-back UART 8N1 frames without a UART-specific RTL state machine?

## Local observation

The final collector run `20261005T062250949951Z` returns zero and passes all
11 stages. `local-manifest.json` is the original, unmodified collector manifest.
It records baseline HEAD `081a8b14a68ff58d46c3b75d53b7138dbea79433` with dirty
UART implementation files, not a clean tested UART commit. Its source hashes
identify the tested RTL, model, formal checker and testbench; later editorial
updates to reports do not make the manifest a clean-commit observation.

Command on Windows, using the repository's isolated Docker configuration:

```powershell
.\tools\workbench.ps1 Evidence
```

| Check | Result |
|---|---|
| Exact-version doctor, static/model, learning status, lint | PASS; 18 model tests |
| Icarus / Verilator | PASS; 14 cocotb tests each |
| GL-shaped smoke / waveform provenance / M0 learning waveform | PASS; not gate-netlist evidence |
| Engine proof and covers | PASS; engine proof 164 seconds wall time |
| Wrong-WAIT mutant | Expected FAIL; mutation test PASS |
| Program store, data store, input synchronizer proofs and covers | PASS |
| Generic synthesis | PASS; zero structural problems |
| Independent review | No blocking findings in final minimized RTL/contract |
| Exact-head CI | Pending publication |
| New physical flow | NOT RUN |

The frame-only oracle checks every byte in both payload slots at legal period
two and four retained complementary pairs at the exact 434-edge period. The
independent model checks all 256 pairs at period 434. Direct traces add both
orders, nonzero RX, slot reuse and arbitrary external changes during a burst.
The integrated public read sees RX capture on the eighth bit before another
clock edge. The frozen contract is `docs/specs/p-uart-tx-8n1.md`.

## Structural measurement

Generic Yosys JSON and synthesis log hashes are retained in the manifest. Cell
counts exclude hierarchical instance cells; state counts count single-bit
mapped DFF primitives, not wires or status ports.

| Module | Abstract cells | State bits |
|---|---:|---:|
| Program store | 1646 | 261 |
| Engine | 1003 | 108 |
| Data store | 84 | 25 |
| Input synchronizer | 16 | 16 |
| Top-level glue (excluding four module instances) | 34 | 0 |
| Complete candidate | 2783 | 410 |

The K-SHIFT-8 baseline has 2534 cells and 385 bits, giving a +249/+25 delta.
The added state is payload byte 8 + period 16 + selector 1. An earlier local
screen had 412 bits; replacing its two retained mode flags with `period != 0`
saves two state bits while leaving the total generic cell count unchanged.
This is a measured ablation, not a proof of minimum substrate size.

## Review and failed attempt

Independent review checked reset/enable, manual compatibility, invalid fields,
final hold, slot selection, same-edge completion, formal properties and both
simulator logs at engine SHA-256
`f13f2c8e2fa7dae9fdf79ed3ebdc0012b7599485d2f211024e0dd4868e3f74fa`.
It reported no blocking issue. One optional future test is a burst/completed
manual-byte/burst sequence; that optional suggestion is not a hidden pass gate.

An earlier checker induction attempt failed before the reachable-state period
invariant was explicit. It is reported in the progress report, not relabelled
as PASS. The retained final formal log contains the successful proof and the
deliberately failing mutant; these must not be confused with that earlier
checker-development failure.

## Boundaries

These results qualify the declared digital UART-TX workload only. UART RX,
baud tolerance, electrical pads, CMOS5L area/timing/fit, new gate-level tests,
FPGA and silicon remain NOT_EVALUATED. The 50 MHz point is a target, not Fmax.
The Tiny Tapeout interface, 6x4 allocation and physical config are unchanged.
M0 human fluency remains PENDING; no learning record is promoted.

Next executable action: publish the committed branch as a draft PR and qualify
its exact head in CI. No merge, hardware purchase or competition submission is
performed by this evidence record.
