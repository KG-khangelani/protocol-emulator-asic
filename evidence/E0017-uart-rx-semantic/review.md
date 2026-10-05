# Independent RX reference review - 2026-10-05

Read-only review found no meaningful correctness/evidence blocker in the
contract, oracle, focused reference cases or scope boundaries.

It checked quarter-tick edge ordering, the raw edge-2 input shortcut against
the specified synchronizer latency, idle/arming prerequisites, even P4..32766,
WAIT/BURST/LOOP timing, bad stops in either frame, pre-validation raw capture
and the overwritten first result. All four recorded E0017 source hashes match;
src/ and formal/ are unchanged and git diff --check is clean.

The reviewer independently ran:

```powershell
python -B -m unittest discover -s test -p test_uart_rx_oracle.py -v
```

All focused groups passed in 1.831 seconds. No files were edited. This review
supports semantic feasibility only; UART-RX RTL and delivery remain unevaluated.
