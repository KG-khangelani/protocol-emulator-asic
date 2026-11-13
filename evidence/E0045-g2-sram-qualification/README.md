# G2 SRAM qualification and adoption evidence

The [complete official physical audit](ci-94a3082/README.md) passes at source
`94a30825c633778b8fb1b8374b79d1a419d3fc96`, run 43348171110. GDS, all ten
prechecks and all eighteen public netlist groups pass. The six original ZIPs,
1,713 original members, 55 producing inputs and completed job/API records are
retained. Windows and pinned Linux replays agree; five corruption controls are
rejected, including three controls whose changed archives are correctly rehashed.

The qualified circuit is the exact E0042 `od128-sram` candidate: one generic
programmable engine, 128 logical words, 8,192 physical macro bits, 353 standard
register bits and interface 0x22. E0042 supplies both complete 30-group RTL
suites and the source-matched compositional proofs. E0044 supplies the complete
normal-command verification on those same sources and models. E0043's corrected
two-simulator pair uses the exact submitted netlist:
`2a0304aebbb2c9a287cc16ac0e61221116c4f2001420baa7df9c0ab1f035cd2e`.

The pinned 8x4 flow retains its 20 ns target, all 80 original stages and five
explicit construction/guard stages. Worst reported setup slack is
5.5958856909900625 ns and hold slack is 0.12079138031701087 ns. Required DRC,
LVS, antenna, power and electrical conditions pass. The official GDS is
`51ac3c1005fd0d811a3e26fddf81fd996a2d57b45172a68670df05e4c57dbbf4`.
The fast corner combines -40 C standard cells and -55 C SRAM. These are digital
flow measurements and functional zero-delay netlist tests, not fabricated
silicon, maximum-frequency or analog-bus qualification.

D43-D47 retain the power construction, nine input buffers, fixed-pin guard,
exact two-file Magic contact-rule alignment and external supply-port selection.
Earlier original-rule, pin-span, timing, congestion and proof-timeout failures
remain in their original evidence directories. G1's compact10 qualification,
P rejection, M0's 6x4 results and owner-fluency status are unchanged.

D48 now adopts all twenty physical inputs byte for byte and binds the decision,
metadata and supporting evidence in the production profile. The
[local adoption screens](adoption/README.md) pass 127 repository tests, style,
generic synthesis, exact physical regeneration and the complete atlas checks.
[Clean actual-default-command CI](ci-default-75c1e7d/README.md) now passes all
eight stages at 75c1e7d/run43361418837, with thirty groups per simulator and two
fresh 127-test executions. Its original 1,922-file ZIP, 329 producing inputs,
actual immutable image identity and complete semantic results pass audit; a
fresh frozen Linux replay reproduces every result and member hash.

The [release tools](release-tools/README.md) preserve the complete research
trail and check publication against these exact inputs. [Alpha.6 publication](publication/README.md)
now passes: all 28 assets downloaded anonymously and hashed, 1,369
curated members identical to committed bytes, complete publication-stage checks,
matching public image/source/version identities and eight passing tag workflows.
The [completion audit](completion-audit.json) closes all nine mandatory workloads
and every G2 requirement. The [final follow-up checks](completion-check/README.md)
retain 127 passing repository tests and verify that all 329 CI inputs are unchanged.
G3 and final submission readiness remain separate.
