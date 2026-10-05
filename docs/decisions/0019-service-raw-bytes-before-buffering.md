# D19 - Quarantine raw byte one under a bounded host deadline

Date: 2026-10-05. Status: adopted bounded digital experiment; no hardware change.

Use the existing nonintrusive read path to preserve two bytes in an external
host cache, but accept them only after both stop checks and normal HALT. The
first raw capture need not be independently frame-accepted: keeping it
tentative until terminal success extends service from the post-stop 9P window
to the full 10P raw-register lifetime. The integer-edge polling/read contract
requires H+L<=10P; asynchronous/physical service still needs a measured bound.

Freeze and falsify this host-assisted bounded workload before adding a FIFO or
second RX slot. It does not provide unserviced two-byte on-chip retention; a
missed deadline can silently return the second byte twice with no chip error
flag. Retain that counterexample rather than widening the claim. If an actual
host cannot meet the contract, queue/error/service semantics must precede a
minimal buffer implementation and cost measurement. M0 learning remains pending.

See `specs/p-uart-rx-host-service.md`. This is an alternative to, not a rewrite
of E0018's historical final-byte-only delivery qualification.

E0019's local/clean CI at `9379d68` and independent review support this exact
host contract. The overwritten-first-byte counterexample remains a limit;
no queue is implemented and no asynchronous/physical service claim follows.
