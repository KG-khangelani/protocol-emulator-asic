# Routed electrical failures and the local-buffer screen

The first integrated full trial clears global routing, detailed-routing DRC,
antenna, power-grid and disconnected-pin checks. Extracted setup and hold are
positive at all three declared model sets: the minimum margins are
5.584762 ns and 0.126718 ns. It nevertheless fails the unchanged electrical
gate. Nine slow-corner SRAM inputs exceed their 0.5952 ns slew limit; the
worst, A_ADDR[2], reaches 1.385473 ns. Fast and typical sets also have slew
violations. The fast model set uses standard cells at -40 C and the vendor
SRAM at -55 C; this is not an isothermal -40 C SRAM characterization.

The separately declared second run enables only the existing post-global-route
design-repair stage. It finds five estimated violations but inserts/resizes
zero cells. Its final extracted result has the same nine violations and the
same minimum timing margins. Both runs are rejected. Their still-running
Magic DRC checks were deliberately stopped after that decisive electrical
failure, at 1,624.545 and 961.973 seconds respectively. Partial GDS output is
retained as diagnostic evidence. Magic DRC, subsequent extraction/LVS and
remaining checker stages are incomplete; no physical qualification is claimed.

A 300-second diagnostic with a stricter 0.4 ns implementation target finishes
in 20.879 seconds. It resizes seven cells and inserts 16 buffers but retains
82 typical-corner estimated violations of that target. It is not adopted.

Actual extracted-database inspection identifies small drivers and long wires
at the affected inputs. A separate 300-second screen inserts nine native buf_4
cells at those macro loads and finishes in 16.838 seconds. Fresh typical-corner
estimated slew violations become zero. No fresh other-corner or extracted
timing result is inferred from this diagnostic. The 0.4 ns setting is absent.

The actual OpenDB audit requires precisely nine new combinational cells and
nine new nets. Collapsing them recovers every original connection and cell
master; public pin geometry, SRAM placement and clock/state connections are
preserved. Native legalization may move original cells. The auditor accepts
the baseline and rejects two actual rewired databases: crossed address loads
and a wrong buffer input. The retained database replay repeats all three checks.

Four archives retain 1,744 files, including inputs, exact scripts, actual
databases, extracted reports, runtime identities and observed failures. Bulk
intermediate views omitted from curation remain hash-indexed. Replay:

```console
python evidence/E0043-sram-physical-integration/electrical/verify.py --output build/sram-electrical-replay
```

Then run `replay_odb.py --directory /workspace/build/sram-electrical-replay`
inside the pinned physical image, with this repository at `/workspace`.

A third fresh full run uses the nine-buffer stage with a fatal connectivity
audit. It preserves all 80 original stages, the verified power stages and all
original acceptance limits. Its full physical outcome remains a separate gate.
