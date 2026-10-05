# E0017 - UART-RX semantic scheduling and falsification

The bounded next milestone is a contract and independent waveform/schedule
oracle, not production receive RTL. The frozen proposed contract is
`docs/specs/p-uart-rx-8n1.md`; D17 records the delivery boundary.

The focused host command passes on Python 3.14.6:

```powershell
python -m unittest discover -s test -p test_uart_rx_oracle.py -v
```

It confirms exact raw-byte capture and HALT timing for the complete byte
alphabet, retained sub-clock phases and the smallest legal reference period.
Missing starts and high-at-start-center fault within their specified bounds;
bad stops in either frame fault even though raw capture has already happened.
The generator rejects the overflowing 2P timeout. `result.json` records source
identities and proof boundaries. This focused check took 1.928 seconds; runtime
is explanatory, not a substrate-selection metric.

At the coherent review boundary, locked `Doctor` and `Check` also pass on
Python 3.11.16; the RX reference group takes 4.081 seconds there. No broad local
HDL/formal rerun was added while iterating on this unchanged-hardware contract.
Required aggregate CI remains the publication gate.

Independent read-only falsification confirmed the timing at P4 and P434 and
identified the 16-bit timeout range, flush/arming prerequisites, exact-edge
ordering and limited short-start claim before the contract was frozen.
Final read-only review found no meaningful correctness/evidence blocker,
verified all four source hashes, confirmed no src/formal changes and reran the
focused reference check successfully; see `review.md`.

No source under src/ or formal/ changes in this milestone. The model witness
uses the existing eight-word capacity. No new synthesis was needed while
iterating because hardware is unchanged; E0016's generic screen remains a
prior observation, not a new RX resource or physical measurement.

P-UART-RX-8N1 remains NOT_EVALUATED at the RTL rung. Raw-valid is not frame-valid,
and the single result register does not retain both received bytes after HALT.
The next executable action is the public-pin RX/delivery experiment using this
oracle, followed by focused independent review and the required aggregate CI.
M0 owner fluency remains PENDING.
