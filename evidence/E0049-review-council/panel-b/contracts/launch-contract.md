# Selected-project handoff screen

Frozen for the November 24 technical review at 14:37:12 UTC, before simulation.
The work tests a possible host procedure on the existing 0x22 RTL. The G3
loading contract and its historical results remain the reference.

**Question.** Can the host keep the project selected for every reset, identify,
write, read, commit and warm-up edge and obtain the same public execution prefix?
Tiny Tapeout's IHP 0p4 CMOS5L mux uses the same selection to enable the project,
pass its clock/inputs and control power. Its pinned RTL is a precedent for the
eventual competition shuttle. The competition says a deselected design loses state.

**Pair.** Drive one production RTL instance with the public assembler's existing
plan. Drive a second instance with `ena=1` on every edge. Keep the same
read/write data and addresses except for both idle-flush steps. For those two
steps, select `E7`, an ignored loader write. Both host and chip release the
shared pins before attaching the target's settled idle levels. Leaving load
mode follows `E7 -> 67 -> 00` with the core clock stopped, clearing bit 7
before changing any other selector bits. Each instance's input reads back
its own driven bits, with the declared external value on released bits.

**Inputs and observations.** Use the thirteen versioned G3 assembly files, both
G5 waveform files and a synthetic WAIT_PIN on the first instruction that can
only succeed when both synchronizer stages have captured the required level.
Check each public plan expectation on both devices. For each of the fifteen
published examples compare GPIO direction, driven value, status, TX0/TX1,
raw RX/valid, bank, full PC and interface for the first 64 execution edges at
static external idle. This is a launch-prefix experiment. Replies, protocol
transactions, physical pad/mux propagation and silicon are outside its scope.

**Falsification.** The synthetic program starts with a zero-timeout high
sample while residue from the last TX1 read is low. Two settled idle clocks
must allow a literal SET and HALT. Leaving only the last warm-up edge with the
correct idle must fault at PC zero. Replacing the ignored write with a bank
selection must invalidate ready. Inserting an `A7` selector between `E7`
and runtime must visibly enable all eight shared project drivers. An incorrect
result, mismatch on the positive pair or missed negative rejects the screen.

**Cost.** One Icarus compile, production digital SRAM, public-port observations,
under 15 minutes and 8 MiB of H: scratch. Retain errors and the actual run.
No package, qualified input, published asset or historical evidence is edited.
