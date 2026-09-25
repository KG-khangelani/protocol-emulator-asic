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
lock = json.loads((ROOT / "tools/workbench/toolchain.lock.json").read_text())
fast_ci = lock["fast_ci"]
test_workflow = (ROOT / ".github/workflows/test.yaml").read_text()
require(f"runs-on: {fast_ci['runner']}" in test_workflow, "fast CI runner differs from toolchain lock")
for action, commit in fast_ci["actions"].items():
    require(f"uses: {action}@{commit}" in test_workflow, f"fast CI action differs from lock: {action}")
for workflow in (ROOT / ".github/workflows").glob("*.yaml"):
    workflow_text = workflow.read_text()
    for action_ref in re.findall(r"^\s*uses:\s*([^\s#]+)", workflow_text, re.M):
        if not action_ref.startswith("./"):
            require(re.search(r"@[0-9a-f]{40}$", action_ref), f"mutable action ref in {workflow.name}: {action_ref}")
physical = lock["official_cmos5l_qualification"]
gds_workflow = (ROOT / ".github/workflows/gds.yaml").read_text()
require(f"runs-on: {physical['runner']}" in gds_workflow, "physical runner differs from toolchain lock")
require(f"uses: actions/checkout@{physical['checkout_action_commit']}" in gds_workflow, "physical checkout action differs from lock")
for action_path in ("", "/precheck", "/gl_test", "/viewer"):
    expected = f"uses: TinyTapeout/tt-gds-action{action_path}@{physical['outer_action_commit']}"
    require(expected in gds_workflow, f"physical action differs from lock: {action_path or '/'}")
for expected in (
    f"tools-repo: {physical['support_tools_repository']}",
    f"tools-ref: {physical['support_tools_commit']}",
    f"librelane-version: {physical['librelane']}",
    f"pdk: {physical['pdk']}",
):
    require(expected in gds_workflow, f"physical workflow input differs from lock: {expected}")
workbench_sh = (ROOT / "tools/workbench.sh").read_text()
require('--user "$(id -u):$(id -g)"' in workbench_sh, "Linux workbench must preserve host workspace ownership")
require("--env HOME=/tmp" in workbench_sh, "Linux workbench user needs a writable temporary home")
print("PASS: metadata, pinout, source list, top module, clock target, Python syntax, immutable direct workflow refs, locked CI/physical inputs and Linux workspace ownership")
print("LIMIT: no RTL simulation, HDL elaboration, IHP synthesis or physical verification performed by this check")
