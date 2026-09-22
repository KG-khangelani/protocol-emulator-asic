"""Capture reproducible source identities and actual local results; fail closed."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
out = ROOT / "build/evidence" / stamp
out.mkdir(parents=True, exist_ok=False)
def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

manifest = {
    "created_utc": stamp,
    "git_head": git("rev-parse", "HEAD"),
    "git_status": git("status", "--porcelain"),
    "python": platform.python_version(),
    "platform": platform.platform(),
    "source_sha256": {}, "tools": {}, "stages": [],
    "physical_status": "NOT_RUN: use official CMOS5L GDS workflow; generic synthesis is not physical fit",
}
names = git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
for name in sorted(set(names)):
    p = ROOT / name
    if p.is_file() and not name.startswith(("evidence/", "build/")):
        manifest["source_sha256"][name] = hashlib.sha256(p.read_bytes()).hexdigest()
for binary, flag in (("iverilog", "-V"), ("vvp", "-V"), ("yosys", "-V"), ("git", "--version")):
    path = shutil.which(binary)
    if path:
        r = subprocess.run([path, flag], capture_output=True, text=True, timeout=30)
        manifest["tools"][binary] = (r.stdout + r.stderr).splitlines()[0]
    else:
        manifest["tools"][binary] = "MISSING"
for package in ("cocotb", "PyYAML"):
    try:
        manifest["tools"][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        manifest["tools"][package] = "MISSING"

stages = [
    ("static", [sys.executable, "tools/check_project.py"], []),
    ("rtl", ["make", "test"], ["iverilog", "vvp", "cocotb-config"]),
    ("generic_synthesis", ["make", "synth"], ["yosys"]),
]
for name, command, required in stages:
    missing = [x for x in required if not shutil.which(x)]
    stage = {"name": name, "command": command}
    if missing:
        stage.update(status="BLOCKED", missing=missing)
        log = "Missing prerequisites: " + ", ".join(missing) + "\n"
    else:
        try:
            r = subprocess.run(command, capture_output=True, text=True, timeout=300)
            stage.update(status="PASS" if r.returncode == 0 else "FAIL", returncode=r.returncode)
            log = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            stage.update(status="FAIL", reason="timeout after 300 seconds")
            log = stage["reason"] + "\n"
    (out / (name + ".log")).write_text(log)
    manifest["stages"].append(stage)
    print(name + ": " + stage["status"])
for source in ("test/results.xml", "test/tb.fst", "build/synthesis.log", "build/synth.json"):
    p = ROOT / source
    # Never copy stale artifacts from a stage that did not pass in this run.
    stage_name = "rtl" if source.startswith("test/") else "generic_synthesis"
    if p.exists() and next(s for s in manifest["stages"] if s["name"] == stage_name)["status"] == "PASS":
        shutil.copy2(p, out / p.name)
manifest["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(out.relative_to(ROOT))
sys.exit(0 if all(s["status"] == "PASS" for s in manifest["stages"]) else 1)
