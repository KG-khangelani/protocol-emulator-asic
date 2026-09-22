"""Repository consistency checks only; not an HDL compiler or physical check."""
import ast
import json
from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]

def require(condition, message):
    if not condition:
        raise SystemExit(message)

info = yaml.safe_load((ROOT / "info.yaml").read_text())
project = info["project"]
require(info["yaml_version"] == 6, "unexpected Tiny Tapeout metadata version")
require(project["tiles"] == "6x4", "competition allocation must be 6x4")
top = project["top_module"]
require(top.startswith("tt_um_"), "invalid Tiny Tapeout top prefix")
require(set(info["pinout"]) == {f"{p}[{i}]" for p in ("ui", "uo", "uio") for i in range(8)}, "pinout differs from template")
sources = project["source_files"]
require(bool(sources) and len(set(sources)) == len(sources), "empty/duplicate source list")
for name in sources:
    require((ROOT / "src" / name).is_file(), f"missing RTL source: {name}")
rtl = "\n".join((ROOT / "src" / f).read_text() for f in sources)
require(re.search(r"\bmodule\s+" + re.escape(top) + r"\b", rtl), "top module missing")
require(top in (ROOT / "test/tb.v").read_text(), "testbench top mismatch")
listed = re.search(r"^PROJECT_SOURCES\s*=\s*(.+)$", (ROOT / "test/Makefile").read_text(), re.M)
require(listed and listed.group(1).split() == sources, "test/source list mismatch")
config = json.loads((ROOT / "src/config.json").read_text())
require(abs(1e9 / project["clock_hz"] - config["CLOCK_PERIOD"]) < 1e-9, "clock target mismatch")
for folder in ("tools", "test"):
    for file in (ROOT / folder).glob("*.py"):
        ast.parse(file.read_text(), filename=str(file.relative_to(ROOT)))
for workflow in (ROOT / ".github/workflows").glob("*.yaml"):
    require(isinstance(yaml.safe_load(workflow.read_text()), dict), f"invalid workflow: {workflow.name}")
print("PASS: metadata, pinout, source list, top module, clock target, Python syntax and workflow YAML")
print("LIMIT: no RTL simulation, HDL elaboration, IHP synthesis or physical verification performed by this check")
