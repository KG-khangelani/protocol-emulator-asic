# SPDX-License-Identifier: Apache-2.0
"""Run the independent oracle tests and retain inputs, outcomes and witnesses."""
import argparse
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "test"))
import test_i2c_oracle as tests


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/i2c-oracle")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    records = []
    seen_witnesses = set()
    current = [""]
    original = tests.assess
    original_abort = tests.assess_abort

    def observe(rows, case, **control):
        report = original_abort(rows, case, **control) if control else original(rows, case)
        blob = canonical({"case": asdict(case), "control": control, "rows": rows})
        errors = sorted({e["kind"] for e in report["errors"]})
        record = {"index": len(records), "test": current[0], "case": asdict(case),
                  "control": control, "trace_sha256": hashlib.sha256(blob).hexdigest(),
                  "rows": len(rows), "outcome": report["outcome"], "errors": errors}
        key = (current[0], tuple(errors), control.get("control"))
        retain = errors or control or current[0] == "test_hand_calculated_write" or case.timeout_release
        if retain and key not in seen_witnesses:
            seen_witnesses.add(key)
            name = f"witness-{len(seen_witnesses):03d}.json"
            (out/name).write_bytes(canonical({"case": asdict(case), "control": control,
                                            "rows": rows, "report": report}))
            record["witness"] = name
        records.append(record)
        return report

    class RecordingResult(unittest.TextTestResult):
        def startTest(self, test):
            current[0] = test._testMethodName
            super().startTest(test)

    tests.assess = observe
    tests.assess_abort = observe
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordingResult).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(tests.I2COracleTests))
    (out/"unittest.log").write_text(log.getvalue(), encoding="utf-8")
    (out/"cases.jsonl").write_bytes(b"".join(canonical(r) for r in records))
    source_paths = ["tools/i2c_oracle.py", "tools/i2c_reference.py", "test/test_i2c_oracle.py",
                    "experiments/i2c/qualify_oracle.py", "docs/specs/p-i2c-controller-100k.md"]
    counts = {}
    for r in records:
        key = "rejected" if r["errors"] else r["outcome"]
        counts[key] = counts.get(key, 0)+1
    summary = {"schema": 1, "scope": "INDEPENDENT_DIGITAL_ORACLE_FIXTURES_ONLY",
               "status": "PASS" if result.wasSuccessful() else "FAIL",
               "parent_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "seed": tests.SEED, "quantum_ns": 5, "tests": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors),
               "observations": len(records), "counts": counts, "witnesses": len(seen_witnesses),
               "source_sha256": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths},
               "limits": ["No DUT execution, ISA extension or physical qualification",
                          "Event completeness is a trace-adapter obligation",
                          "Ideal digital pull-ups; no analog pad/RC/MTBF result",
                          "Public loader isolation and two disabled flush edges required",
                          "RX provenance for equal old/new bytes also needs RTL/formal checks"]}
    (out/"qualification.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    artifacts = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS")
    (out/"SHA256SUMS").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in artifacts), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "source_sha256"}, indent=2))
    if not result.wasSuccessful():
        print(log.getvalue())
        raise SystemExit(1)


if __name__ == "__main__":
    main()
