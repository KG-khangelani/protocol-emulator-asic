# Independent read-only review

Reviewer: `/root/uart_independent_review`, 2026-10-05. No files changed by
reviewer and no concurrent simulator runs against collector artifacts.

Policy review found no architectural blocker. It requested an explicit
uninterrupted `ui_in[7]=0` precondition (now in the RX contract) and fixed-period
clock budgeting while reading. The reviewed driver totals exactly 20,000ps
per execution cycle, including all subcycle read settles. It judges public pins
against frame mathematics, not `Machine.edge`, and checks raw capture before
stop, FAULT rejection despite raw-valid, final-only delivery, timeouts and abort.

Implementation review identified a release-blocking provenance integration
issue: the validator still required only module `test` while the new regression
contains `test_uart_rx_public` too. Re-review confirms strict acceptance of
exactly those two modules, with subset/unknown/smoke/overwrite rejection intact.
The FORMAL-only syntax correction is compatible with the declared SV proof read
and does not change production Verilog. No other RTL or RX-policy defect found.

Reviewer independently confirmed the initial failed manifest is byte-identical
to its original (`0e7d33cd698e242777a88c47b7f610f283d474c3f0a71709160f37c3d7451de5`)
and both archived failure logs match their manifest hashes. The original run
honestly records lint/provenance FAIL and functional/formal PASS. Independent
netlist recount is 2,793 cells/410 state bits, top glue 44/0; submodule resources
are unchanged. Metadata changes are descriptions only: official ports, source
list, `src/config.json` and 6x4 allocation are preserved.

Reviewed implementation anchors (SHA-256):

| File | Hash |
|---|---|
| `src/project.v` | `0a391b4b283f563b59a49520992af693df102420e8ee34d826b6f72535a4609f` |
| `test/test_uart_rx_public.py` | `15f5e901578ce5a6322c639c2fab520c731c2b38e239564c8311c99a0ddc426b` |
| `tools/check_waveform_provenance.py` | `f3f4efe08fbbb32d18bc2ba0867cce16a9b4327bb669d9065148a65a41f65e24` |
| `test/test_waveform_provenance.py` | `2805707d1a425eec2df60d96784560eb5cb5bd959668becb18516034e3093221` |
| `formal/m1_public_readout.sby` | `af84ce76016500af01d63282502c496c66c03a4eda0c126d7843fba6c4e6008c` |

Conclusion: no remaining review blocker. The frozen-tree aggregate and exact
committed-head CI must still pass before integration. This review does not
promote owner fluency or physical/complete-UART claims.

## Clean implementation CI and qualification-record re-review

Reviewer independently checks clean head
`181cfa19b2d05f0892bfb8e6ebb5e234b9a18f03`, all eleven passing collector stages,
all 31 extracted artifact hashes and all 130 source hashes against Git blobs at
that commit. Curated CI manifest/JUnit files are byte-identical to originals;
manifest SHA-256 is
`cb84133515ca08c5f9e0fdf53a496edf33fa329f6440d88e5abb744c7f54fb1f`.
Both simulator reports contain the original and RX modules, with no failures,
errors or skips. Independent CI netlist recount is 2,793 cells/410 state bits.

Only docs/evidence change after the implementation commit. Review confirms
accurate GitHub-reported/unverified ZIP-digest attribution, final-only batch
delivery and host-abort limits, loader/runtime pin ownership, and the derived
9P=3,906-clock/78.12-us window NOT being a delivery proof. Final-record CI and
normal integration are explicitly tracked separately at PR7. No remaining
blocker before the record commit and its own exact-head CI; no merge, physical
or human-fluency pass is inferred.
