# D40 - Verify the current source and preserve historical contracts

Date: 2026-11-12. Status: integration preparation; production unchanged.

The unchanged default test suite rejects four D39 behaviors because its
expectations describe the original eight-word store and five-bit program
counter. E0038 retains that failed integration probe. D39 has 128 real words,
an eight-bit program counter and the declared general open-drain instruction
extension. Treating old capacity or encoding limits as current requirements
would misdescribe the new interface.

Use an explicit source profile selected from the actual five RTL file hashes.
The original source selects `legacy8`; the frozen D39 source selects
`od128-shared`. Unknown source bytes fail selection. Production keeps its
original profile until the complete physical gate permits adoption.

The current profile checks invalid length 129, the representable PC32 followed
by invalid fetch, and a genuinely reserved manual shift bit. Direct-engine
PC and loop-address observations use all eight bits. Keep every existing
default test identity and add the full UART/SPI/I2C, boundary and abort matrix:
30 groups in each simulator, including both public loading and direct-core
checks. The independent reference records remain exact. An additional public
control writes and reads the highest word without aliasing lower words and
checks invalid-bank cleanup. The original 22 groups also run on the unchanged
historical source with their original expectations.

Current formal verification uses the actual candidate files: complete-chip
equivalence and reset base, general-instruction proofs/covers and checked
mutations, data-store and synchronizer properties/covers, public readout and
the host deadline lemma. The complete original ten formal tasks remain on the
hash-checked E0020 baseline, with their original properties and depths. Their
results are explicitly historical; they are not relabelled as current-chip
proofs. The D38 store proof and D39 complete-chip equivalence remain separate
parts of the qualification chain.

Route normal `make` verification commands through the selected profile. An
explicit `SOURCE_DIR` can exercise the candidate before production adoption.
Keep the full current RTL public traces, direct-core results and a separate
RTL harness smoke waveform under distinct labels. The smoke waveform is not
actual-netlist evidence. Preserve the original waveform provenance rules for
the historical profile and the archived M0 learning path.

Evidence collection always runs the quick repository checks fresh: their
learning/history metadata extends beyond the RTL input set. A retained
isolated counterexample demonstrates why the first collector's cached check
was insufficient. Long verification stages may be reused only when their actual source,
verification code/configuration, pinned runtime and retained artifact bytes
match. Recheck test identities, reference observations and formal witnesses;
a failed, skipped or incomplete stage cannot supply a pass. Run missing or
stale stages explicitly; inspect an unfinished stage before retrying it. Save
the exact verification inputs with the retained artifacts so later changes
cannot silently redefine this result. CI exercises the prospective profile
separately while production remains historical.

This decision changes verification and its evidence labels. D39 production
promotion, physical acceptance and publication still require every gate in
[the integration specification](../specs/g2-production-integration.md).
G1's qualification, failed alternatives and owner-fluency status are preserved.

E0039 retains 30 passing groups in both simulators and all 22 historical groups
in both. Initial current and complete historical formal runs pass. The later
normal-command temporal proof times out at 300 seconds, so that command run
remains incomplete despite seven other passing stages. Its exact retained
replay also reproduces the first collector's metadata-cache gap. The installed
fresh-check repair passes its focused controls and all 114 repository checks;
complete current-command CI subsequently passes at 8488738 in run43267588725.
E0039's original 1,532-file current-candidate ZIP and 250 exact verification
inputs are audited: all eight stages pass, including the temporal proof in
108.405 seconds within the same 300-second budget, and collection reruns all
114 metadata checks. The earlier timeout remains unchanged. D39 still fails
physical qualification; no production promotion follows from this result.
