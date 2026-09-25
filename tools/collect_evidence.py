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
    "formal_status": "PENDING",
    "physical_status": "NOT_RUN: use official CMOS5L GDS workflow; generic synthesis is not physical fit",
}
names = git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
for name in sorted(set(names)):
    p = ROOT / name
    if p.is_file() and not name.startswith(("evidence/", "build/")):
        manifest["source_sha256"][name] = hashlib.sha256(p.read_bytes()).hexdigest()
tool_commands = {
    "git": ["git", "--version"],
    "g++": ["g++", "--version"],
    "iverilog": ["iverilog", "-V"],
    "vvp": ["vvp", "-V"],
    "verilator": ["verilator", "--version"],
    "verible": ["verible-verilog-lint", "--version"],
    "yosys": ["yosys", "-V"],
    "sby": ["sby", "--version"],
    "z3": ["z3", "--version"],
    "boolector": ["boolector", "--version"],
}
for name, command in tool_commands.items():
    path = shutil.which(command[0])
    if path:
        r = subprocess.run(command, capture_output=True, text=True, timeout=30)
        output = next((line for line in (r.stdout + r.stderr).splitlines() if line.strip()), "")
        manifest["tools"][name] = output
    else:
        manifest["tools"][name] = "MISSING"
for package in ("cocotb", "PyYAML"):
    try:
        manifest["tools"][package] = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        manifest["tools"][package] = "MISSING"

stages = [
    ("doctor", [sys.executable, "tools/doctor.py"], []),
    ("static", [sys.executable, "tools/check_project.py"], []),
    ("learning_status", [sys.executable, "tools/learning_status.py", "--verify"], []),
    ("lint", ["make", "lint"], ["verible-verilog-lint"]),
    ("rtl_icarus", ["make", "test"], ["iverilog", "vvp", "cocotb-config"]),
    ("learning_waveform", ["make", "learn-waveform"], ["iverilog", "vvp", "cocotb-config"]),
    ("rtl_verilator", ["make", "test-verilator"], ["verilator", "g++", "cocotb-config"]),
    ("formal", ["make", "formal"], ["sby", "z3"]),
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
formal_stage = next(stage for stage in manifest["stages"] if stage["name"] == "formal")
if formal_stage["status"] == "PASS":
    manifest["formal_status"] = "PASS: safety proof and wrap covers passed; increment-by-two mutant was rejected"
else:
    manifest["formal_status"] = formal_stage["status"]
artifact_sources = {
    "test/results.xml": ("rtl_icarus", "results.xml"),
    "test/results-verilator.xml": ("rtl_verilator", "results-verilator.xml"),
    "test/tb.fst": ("rtl_icarus", "tb.fst"),
    "test/results-learning.xml": ("learning_waveform", "results-learning.xml"),
    "build/m0-learning.vcd": ("learning_waveform", "m0-learning.vcd"),
    "build/formal/prove/status": ("formal", "formal-prove.status"),
    "build/formal/cover/status": ("formal", "formal-cover.status"),
    "build/formal/mutant/status": ("formal", "formal-mutant.status"),
    "build/synthesis.log": ("generic_synthesis", "synthesis.log"),
    "build/synth.json": ("generic_synthesis", "synth.json"),
}
for source, (stage_name, destination) in artifact_sources.items():
    p = ROOT / source
    # Never copy stale artifacts from a stage that did not pass in this run.
    if p.exists() and next(s for s in manifest["stages"] if s["name"] == stage_name)["status"] == "PASS":
        shutil.copy2(p, out / destination)
manifest["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
(out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(out.relative_to(ROOT))
sys.exit(0 if all(s["status"] == "PASS" for s in manifest["stages"]) else 1)
