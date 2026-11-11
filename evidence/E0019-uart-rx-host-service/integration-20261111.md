# PR8 integration with current main

Status: integration candidate; focused local checks pass, complete validation
pending. This addendum preserves
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

Independent code and conflict-resolution review found no blocker. The complete
evidence ladder and clean remote head remain pending. Local integration checks
do not imply a completed merge; remote outcomes must be recorded by exact run
and commit identities.

## Claim boundary

The original host-service contract and external host-storage accounting remain
unchanged. This integration does not establish autonomous/continuous receive,
an asynchronous operating-system host guarantee, full SPI/I2C, physical timing
or owner fluency. The previous approval rejection in the historical PR record
remains historical; the new explicit owner merge instruction authorizes this
integration and review.
