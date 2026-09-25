"""Explain tool purposes and strictly verify the locked workbench when inside it."""

from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "tools" / "workbench" / "toolchain.lock.json"
STRICT = os.environ.get("PROTOCOL_EMULATOR_LOCKED_WORKBENCH") == "1"


def first_line(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip()), "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
workbench = lock["developer_workbench"]
failures: list[str] = []

dockerfile_text = (ROOT / "tools" / "workbench" / "Dockerfile").read_text(encoding="utf-8")
source_fragments = {
    "base image": f"FROM {workbench['base_image']}",
    "OSS CAD Suite version": f"ARG OSS_CAD_SUITE_VERSION={workbench['oss_cad_suite']['version']}",
    "OSS CAD Suite asset": f"ARG OSS_CAD_SUITE_ARCHIVE={workbench['oss_cad_suite']['asset']}",
    "OSS CAD Suite hash": f"ARG OSS_CAD_SUITE_SHA256={workbench['oss_cad_suite']['sha256']}",
    "Verible version": f"ARG VERIBLE_VERSION={workbench['verible']['version']}",
    "Verible asset": f"ARG VERIBLE_ARCHIVE={workbench['verible']['asset']}",
    "Verible hash": f"ARG VERIBLE_SHA256={workbench['verible']['sha256']}",
    "Python dependency hash": f"ARG REQUIREMENTS_SHA256={workbench['python_requirements']['sha256']}",
}
for package, version in workbench["debian_packages"].items():
    source_fragments[f"Debian package {package}"] = f"{package}={version}"

source_drift = [name for name, fragment in source_fragments.items() if fragment not in dockerfile_text]
if source_drift:
    print(f"FAIL: Dockerfile differs from toolchain lock: {', '.join(source_drift)}")
    failures.append("Dockerfile ingredient declarations differ from toolchain.lock.json")
else:
    print("PASS: Dockerfile ingredient declarations match the machine-readable lock")

mode = "locked workbench: exact versions required" if STRICT else "host inspection: missing tools are reported, not installed"
print(f"MODE: {mode}")

python_expected = workbench["python"]
python_observed = platform.python_version()
python_ok = python_observed == python_expected
print(f"{'PASS' if python_ok else 'FAIL' if STRICT else 'INFO'}: Python {python_observed} — runs project checks and cocotb tests")
if STRICT and not python_ok:
    failures.append(f"Python expected {python_expected}, observed {python_observed}")

for name, specification in workbench["tools"].items():
    command = specification["command"]
    executable = shutil.which(command[0])
    if executable is None:
        status = "FAIL" if STRICT else "MISSING"
        print(f"{status}: {name} — {specification['purpose']}")
        if STRICT:
            failures.append(f"{name} is missing")
        continue

    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        check=False,
    )
    observed = first_line(completed.stdout)
    expected = specification["expected_output"]
    matches = completed.returncode == 0 and observed == expected
    status = "PASS" if matches else "FAIL" if STRICT else "INFO"
    print(f"{status}: {name} — {specification['purpose']}")
    print(f"  observed: {observed or '<no version output>'}")
    if STRICT and not matches:
        failures.append(f"{name} expected {expected!r}, observed {observed!r} (exit {completed.returncode})")

requirements_path = ROOT / workbench["python_requirements"]["path"]
requirements_expected = workbench["python_requirements"]["sha256"]
requirements_observed = sha256(requirements_path)
requirements_ok = requirements_observed == requirements_expected
print(f"{'PASS' if requirements_ok else 'FAIL'}: hashed Python dependency lock")
print(f"  observed: {requirements_observed}")
if not requirements_ok:
    failures.append("Python dependency lock hash differs from toolchain.lock.json")

if STRICT:
    observed_platform = f"{platform.system().lower()}/{platform.machine().lower()}"
    expected_platform = workbench["platform"].replace("amd64", "x86_64")
    platform_ok = observed_platform == expected_platform
    print(f"{'PASS' if platform_ok else 'FAIL'}: workbench platform {observed_platform}")
    if not platform_ok:
        failures.append(f"workbench platform expected {expected_platform}, observed {observed_platform}")

    suite_marker = Path("/opt/oss-cad-suite/VERSION").read_text(encoding="utf-8").strip()
    suite_expected = workbench["oss_cad_suite"]["version_marker"]
    suite_ok = suite_marker == suite_expected
    print(f"{'PASS' if suite_ok else 'FAIL'}: OSS CAD Suite release marker {suite_marker}")
    if not suite_ok:
        failures.append(f"OSS CAD Suite expected marker {suite_expected}, observed {suite_marker}")

    for package, expected in workbench["debian_packages"].items():
        completed = subprocess.run(
            ["dpkg-query", "-W", "-f=${Version}", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30,
            check=False,
        )
        observed = completed.stdout.strip()
        ok = completed.returncode == 0 and observed == expected
        print(f"{'PASS' if ok else 'FAIL'}: Debian package {package} {observed or '<missing>'}")
        if not ok:
            failures.append(f"Debian package {package} expected {expected}, observed {observed!r}")

if failures:
    print("RESULT: FAIL — the environment does not match the recorded ingredient batch:")
    for failure in failures:
        print(f"  - {failure}")
    raise SystemExit(1)

if STRICT:
    print("RESULT: PASS — every required tool matches its recorded version.")
else:
    print("RESULT: REPORT — host inspection complete; any MISSING tool remains unavailable.")
    print("Use tools/workbench.ps1 to run the locked Linux toolchain on Windows.")
print("LIMIT: this proves tool identity, not RTL correctness or physical-chip acceptance.")
