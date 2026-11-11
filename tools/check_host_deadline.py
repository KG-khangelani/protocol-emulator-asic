"""Require actual SMT proof and deliberate weakened-bound counterexample."""

from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
result = subprocess.run(["z3", str(root / "formal/uart_rx_host_deadline.smt2")],
                        text=True, capture_output=True, timeout=30, check=True)
answers = [line.strip() for line in result.stdout.splitlines()
           if line.strip() in ("sat", "unsat", "unknown")]
if answers != ["unsat", "sat"] or "error" in result.stdout.lower():
    raise SystemExit("FAIL: host deadline proof/counterexample: " + result.stdout + result.stderr)
print(result.stdout, end="")
print("PASS: bounded integer-host deadline lemma; weakened-bound counterexample exists")
print("LIMIT: no RTL liveness, asynchronous service or physical access proof")
