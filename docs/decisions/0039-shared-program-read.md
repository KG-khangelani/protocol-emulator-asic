# D39 - Qualify a shared program-word read

Date: 2026-11-12. Status: experimental qualification in progress.

D38's 128-word store retains two independent read-selection networks even
though the complete chip consumes either loader bytes or instructions at a
time. The frozen shared-read screen in E0037 selects the address first and
then reads one word. Generic cells fall from 24,391 to 15,211, with all 4,278
state bits unchanged. This is a generic measurement, not mapped or routed area.

Advance the exact screened source as the separate `od128-shared` candidate
in E0038. Preserve D38 and its physical trial. The builder checks its immutable
parent and the measured/proved source hashes. All writes, real storage,
control transitions, capacity, ISA 0x21, clocks, latency and public pins stay
the same. The engine, data store, synchronizer and top remain byte-identical.

The store's inactive internal instruction/readback ports can differ. E0037
therefore retains both a conditional store comparison and a stronger complete
chip proof: every actual state bit and all 24 public output bits remain
equivalent after reset. The latter compares real complete chips, with no
abstract memory or protocol restrictions; a separate SAT base establishes
correspondence from independent arbitrary state after one sampled reset edge.
Only combinational internal match points are excluded. The temporal proof
closes at step one. These are digital synchronous guarantees.

Before physical trial, require the unchanged eighteen public groups in both
RTL simulators, exact UART/SPI/I2C reference records, and public observations
that distinguish deliberately broken high-bank reads, fetch-address selection
and length readback. Re-run the complete-chip proof with checked source,
state/output coverage and reset base. Preserve actual failures and witnesses.
The D38 narrow complete-byte-case lint exception applies to identical writes.
The measured source also inserted its address wire between the inherited
`always-comb` line waiver and the sole combinational read block. Keep the
measured/proved bytes and explicitly apply that inherited exception to the
hash-checked store. The unwaived log must show exactly 128 complete-byte-case
warnings and that one combinational-style warning; every other rule/module
must pass. The initial lint attempt rejected the extra warning and is retained.

Production promotion still requires the unchanged pinned 8x4 CMOS5L flow,
all routed metrics, ten prechecks and actual-netlist public selection with
verified original artifacts. No capacity, timing or routing threshold is
relaxed. G2 integration and publication remain separate required steps.
