# Progress report: M1 execution contract and implementation

Date: 2026-10-02. Scope: simulation-only specification work.

## Engineering completed autonomously

- Drafted exact SET, WAIT, HALT, reset/enable, PC, GPIO, HALT, and invalid-program
  semantics in `docs/specs/m1-execution-contract.md`.
- Reconciled the subset with the adopted evaluation contract: unsupported
  microkernels, reload, protocol workloads, complete-chip cost, and physical
  results remain `NOT_EVALUATED`.
- Added a reusable synthesizable engine, provisional preload, independent Python
  semantic model, pin-level Icarus/Verilator comparison, formal properties and
  a falsification check. These are pre-physical engineering results.
- Rechecked the official competition page on 2026-10-02: January 18, 2027
  submission deadline, IHP 130 nm CMOS5L, 6x4 maximum allocation, and a
  reprogrammable general-purpose protocol emulator remain the pertinent bounds.

## Learning gate and decisions reserved

M0 technical evidence remains closed, and the owner-fluency checkpoint remains
`PENDING`. By explicit owner approval, engineering now progresses independently;
no learning status was promoted. The provisional encoding remains experimental.

Remaining engineering work includes storage optimization, input synchronization,
bounded event waits, protocol workloads and new CMOS5L qualification. Owner
teach-back remains a separate optional action.

## 2026-10-03 reload milestone

The D9 constant preload is superseded by an eight-word public-pin program store.
Icarus and Verilator each pass four tests, including `P-RELOAD`: load/read/run
program A, reset, then load/read/run observably different program B without RTL
changes. Invalid length remains fail-closed. Engine and store formal proofs and
covers pass, and the wrong-WAIT falsification still produces a counterexample.

Generic synthesis reports 1,879 abstract cells and 300 state elements versus
225 cells for the preload candidate. This quantifies the flip-flop store cost;
it is not CMOS5L area, fit, timing, or Fmax evidence. Exact-head CI is the next
qualification step.

## 2026-10-03 bounded input-wait milestone

The exact-head CI qualification for the reload milestone passed at `d502227`.
The next candidate adds a two-stage `uio_in` synchronizer and a bounded
`WAIT_PIN` primitive. The specification fixes its three-edge earliest response,
accepted-edge timeout accounting, final-edge event priority, reset behavior and
sticky timeout FAULT. Nine model checks and five tests under both Icarus and
Verilator pass. Engine, store and synchronizer formal proofs/covers pass, the
wrong-WAIT mutant is rejected, and generic synthesis reports 1,985 abstract
cells and 321 state elements. Exact-head CI passed at `14a93b4`.

This is autonomous engineering under D8. The owner M0 teach-back remains
`PENDING`; no learning status changed. The primitive is not a protocol kernel,
does not complete `K-INPUT-WAIT`, and has no new physical or silicon evidence.

The existing evidence collector is the right base for later versioned
simulation/RTL release bundles: it already records exact commit, tool versions,
source hashes, JUnit, waveform, formal status and synthesis output. A later
reviewed-milestone workflow should package that manifest and selected portable
artifacts under a signed/versioned tag, clearly distinct from a
physical-fabrication-ready release. No tag or release is created here.

## 2026-10-03 K-INPUT-WAIT milestone

Acceptance was frozen before implementation in `specs/k-input-wait.md`. One
three-word image is loaded and read back through public pins, exercises an
event path, is erased by reset, is loaded/read again, and exercises timeout.
Independent expected pin/status sequences require both paths to HALT at PC2
within six accepted edges and distinguish them with GPIO0.

The minimum semantic delta is D12's one-bit timeout skip on `WAIT_PIN`; no
general branch or protocol-specific RTL was added. Ten model checks, six tests
on each simulator, lint, formal proof/cover/mutation, and generic synthesis pass
in the locked local workbench. The complete candidate maps to 1,971 abstract
cells and 322 state elements. `K-INPUT-WAIT` is therefore PASS/MEASURED only at
the RTL rung; exact-head CI passed at `f383744`, and all physical/silicon claims remain
NOT_EVALUATED.

## 2026-10-03 K-BOUNDED-LOOP milestone

D13 selects bounded repetition before K-SHIFT-8: all target protocols reuse
timed repetition, while a shifter still needs payload loading, received-data
readback, bit order and sampling-phase decisions. Acceptance was frozen before
implementation in `specs/k-bounded-loop.md`.

The public-pin-loaded four-word kernel produces exact independent GPIO traces
for counts 0, 1, 2 and 255, freezes under disable, rejects nesting and HALTs at
the declared `2*N+2` edge bound. Both simulators, 12 model checks, formal
proof/covers/mutation, lint and generic synthesis pass locally. The complete
candidate initially reported 2,198 abstract cells and 341 state elements, a delta of +227
cells and +19 state bits from K-INPUT-WAIT. This is generic structural evidence,
not CMOS5L area, timing or fit. Exact-head CI remains pending.

Independent review then reproduced two blockers. `LOOP(length=31,count=0)` at
PC0 previously narrowed target 32 to five bits and aliased PC0; target addition
is now six bits and out-of-range targets fault at the source PC in RTL, model,
simulation and an independent formal property. The shared cocotb initializer
also referenced direct-engine handles omitted by `GL_TEST`; initialization is
now handle-safe and engine-only tests are skipped in real gate mode. A small
RTL compile/run with the `GL_TEST` harness shape proves public reset works with
those handles absent. It does not claim a generated-netlist or physical run.
After these fixes, generic synthesis reports 2,175 abstract cells and 341 state
elements, or +204 cells and +19 state elements versus K-INPUT-WAIT.
