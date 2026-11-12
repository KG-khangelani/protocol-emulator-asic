# G2 bounded shared-read experiment

Predeclared 2026-11-12 while D38's complete protocol selection is running.
This is an isolated screen; it changes neither D38's frozen source nor its
required physical trial. Do not infer physical feasibility from generic cost.

The current top masks the engine reset whenever public load mode is set.
Program-store data_out is externally selected only during program loading;
instruction fetch is consumed only while that store's load_mode is false.
Register-loading selections that deselect the program store also keep the
engine reset. The program store currently implements separate asynchronous
word-fetch and byte-read selection networks.

Hypothesis: select the loader word address or the PC before one 32-bit word
read, then choose the loader byte after that read. Keep every word, write,
reset, bank/length/ready transition and instruction_valid logic unchanged.
No new clock, latency, pin, instruction, capacity or fixed program is allowed.

The raw internal instruction output may change in store load mode, and raw
data_out may change outside that mode. Those differences are not hidden full
store equivalence. Compare instruction masked to zero in load mode, data_out
masked to zero outside load mode, and all other store outputs normally.
Require sequential equivalence from corresponding state, which the identical
reset establishes. Top-level ownership above is a source-derived premise;
this screen alone is not a full-chip equivalence or protocol qualification.

Bound generic complete-chip synthesis to 300 seconds and conditional store
equivalence to 240 seconds. Record exact source, cells/state bits, proof inputs,
logs and timeout/failure status. Any promising result still needs a separate
decision, public boundary/regression/negative controls and fresh matched
physical evidence before adoption. Do not relax D38 or G2 acceptance gates.
