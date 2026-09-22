"""Fail closed for missing, empty, failing, errored or skipped regressions."""
import sys
import xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
cases = list(root.iter("testcase"))
if not cases:
    raise SystemExit("FAIL: no test cases in JUnit result")
for tag in ("failure", "error", "skipped"):
    if list(root.iter(tag)):
        raise SystemExit(f"FAIL: JUnit contains {tag}")
for suite in root.iter("testsuite"):
    if any(int(suite.get(key, "0")) for key in ("failures", "errors", "skipped")):
        raise SystemExit("FAIL: nonzero JUnit failure/error/skip count")
print(f"PASS: {len(cases)} test cases")
