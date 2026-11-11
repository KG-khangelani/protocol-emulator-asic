# PR8 integration with current main

Status: merged at `7b2f746b608d1685115071c0ae79f64d39c93f2a` after complete
corrected-head PR validation. This addendum preserves
the original E0019 records and does not rewrite their tested revisions or limits.

The owner explicitly requested merging outstanding pull requests on
11 November 2026. This integrates PR8 head
`b19a718e25b2f6e3343a15a1632aaed7da14c05f` with main
`483df6743fd713982d65ec9d7a8e9043344f49fc`, which already contains PR9's atlas,
PR11's isolated SPI experiments and PR10's Vite patch. It merges main into the
existing PR branch without rewriting its history.

Five additive conflicts were resolved: `Makefile`, current state, backlog,
research ledger and evidence index. The resolution keeps both the host-service
and SPI reference checks, all newer decisions/results, and the current SPI
engineering direction. Existing PR8 implementation files merged without a code
conflict. Production RTL, official configuration and source lists are unchanged
relative to current main.

## Validation

The resolved working tree passes the locked `workbench.ps1 Check`: 18 M1 model,
3 UART RX oracle, 3 host-service, 6 SPI oracle, 4 phase-reference, 6 pin-timing
and 4 waveform-provenance tests, plus repository/learning consistency checks.
`python3 tools/check_host_deadline.py` in the locked container returns the
required `unsat` safe-bound proof and `sat` weakened-bound counterexample.
Focused Icarus execution with `COCOTB_TEST_MODULES=test_uart_rx_public` and
`COCOTB_TEST_FILTER=uart_rx_host_service_` passes all three public-pin groups.
The JUnit result is in `integration-20261111-focused-icarus.xml`.

Independent code and conflict-resolution review found no blocker. Atlas build,
19 source/model checks and three focused Chromium cases pass locally at
`f7281cf3d2705b774f4b0080fa5b5ca75e1ee150`. The atlas identifies the retained
E0019 report without claiming to model host service or its external cache.

At that clean source, remote run
[43088833648](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43088833648)
passes all eleven collector stages, including formal and both simulators
(22 cases each). `integration-20261111-ci-manifest.json` retains that result.
Artifact `13888586496`, `verification-f7281cf3d2705b774f4b0080fa5b5ca75e1ee150`,
has GitHub-reported ZIP digest
`33e17af53a8bc784e68d3edf787efb8f7b6df2bedcf30ea85c980cf4667695f8`.

The overall workflow then **failed** in the isolated SPI comparison: every one
of its 20 baseline legacy cases passed, but the acceptance guard still expected
17 cases. PR8 added three host-service cases to that unchanged module list.
The raw failed-step log and JUnit are retained as
`integration-20261111-stale-count.log` and
`integration-20261111-stale-count.xml`. The minimal fix changes the required
count to exactly 20. Zero skips, exact named failures and return-code checks
remain enforced; the banked variant still permits only the known invalid-length
failure. No test is filtered out. Corrected-head CI must pass before merging;
the earlier overall failure remains a failure.

Separately, the same clean source's local collector
`20261111T193637553739Z` passes ten stages but times out in the aggregate formal
stage after 300 seconds. `integration-20261111-local-manifest.json` retains its
**FAIL**. Engine induction had passed while base-case solving remained
unfinished; no local complete formal proof is claimed. The remote formal PASS
is separate evidence, not a rewrite of the local timeout. No timeout budget was
increased. Bulk solver logs and the comparison rerun remain under ignored
`build/`; the clean remote workflow artifacts are the integration authority.

## Final corrected-head qualification and merge

Corrected source `996b967379a5782a6aa666646e8541b6ba98282f` passes the complete
[PR verification run 43091404934](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43091404934),
[atlas run 43091405065](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43091405065)
and [docs run 43091389546](https://github.com/KG-khangelani/protocol-emulator-asic/actions/runs/43091389546).
The full PR run includes the SPI comparisons, core and public integration
properties, pin timing and actual eight-word program induction.

The local corrected comparison also passes all 12 stages. Baseline and compact
each pass 20 legacy cases; banked has 19 passes and only the documented
invalid-length failure, with no skips. Both experimental phase variants pass
four cases on each simulator. Generic cell/state counts remain unchanged.
`integration-20261111-comparison.json` retains the result and experiment/source
hashes; SHA-256 is
`6b26b07c153b4e2591eb3f1b93cd8879c3e880fdbec9b5764611822e80e6bc2d`.

The owner-authorized normal merge used an exact-head guard and no admin bypass.
Its source tree `a7bfb0622c39e3d68bdef2efa69bb70ba2aef0ee` equals the tested
head's tree. The duplicate push verification run `43091389556` was still running
when the merge completed; this is not reported as a pass. Post-merge workflows
were newly triggered and their results are likewise separate. No open PRs
remained at the merge check.

## Claim boundary

The original host-service contract and external host-storage accounting remain
unchanged. This integration does not establish autonomous/continuous receive,
an asynchronous operating-system host guarantee, full SPI/I2C, physical timing
or owner fluency. The previous approval rejection in the historical PR record
remains historical; the new explicit owner merge instruction authorizes this
integration and review.
