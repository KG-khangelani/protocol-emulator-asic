"""Read-only, evidence-backed guided tour of the M0 RTL-to-GDS result."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
E0007 = ROOT / "evidence" / "E0007-locked-fast-ci"
E0010 = ROOT / "evidence" / "E0010-pinned-cmos5l-run"
LOCK = ROOT / "tools" / "workbench" / "toolchain.lock.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def line_number(lines: list[str], text: str) -> int:
    matches = [index for index, line in enumerate(lines, start=1) if text in line]
    require(len(matches) == 1, f"expected one archived RTL line containing {text!r}")
    return matches[0]


def load_model() -> dict:
    fast = read_json(E0007 / "result.json")
    physical = read_json(E0010 / "result.json")
    comparison = read_json(E0010 / "gds-comparison.json")
    raw_metrics = read_json(E0010 / "physical-metrics.json")
    commit_id = read_json(E0010 / "commit-id.json")
    lock = read_json(LOCK)

    source_path = E0010 / "source-project.v"
    source_bytes = source_path.read_bytes()
    source_lines = source_bytes.decode("utf-8").splitlines()
    expected_blob = physical["physical_input_equivalence"]["blob_ids"]["src/project.v"]
    archived_source = physical["physical_input_equivalence"]["archived_source"]

    require(fast["status"] == "success", "E0007 fast CI is not successful")
    require(set(fast["stages"].values()) == {"PASS"}, "not every E0007 stage passed")
    require(
        fast["generic_synthesis"]["physical_fit_evaluated"] is False,
        "generic synthesis must not claim physical fit",
    )
    require(physical["status"] == "success", "E0010 physical workflow is not successful")
    for job in ("gds", "precheck", "gate_level"):
        require(physical["jobs"][job]["status"] == "PASS", f"E0010 {job} did not pass")
    require(
        physical["m0_physical_gate"]["technical_gate_satisfied"] is True,
        "E0010 does not record the technical physical gate as satisfied",
    )
    physical_result = physical["physical_result"]
    with (E0010 / "selected-metrics.csv").open(encoding="utf-8", newline="") as handle:
        selected_metrics = {row["metric"]: row["value"] for row in csv.DictReader(handle)}
    metric_cross_checks = (
        ("final_standard_cells", "design__instance__count__stdcell"),
        ("timing_repair_buffers", "design__instance__count__class:timing_repair_buffer"),
        ("clock_buffers", "design__instance__count__class:clock_buffer"),
        ("worst_setup_slack_ns", "timing__setup__ws"),
        ("worst_hold_slack_ns", "timing__hold__ws"),
        ("route_drc_errors", "route__drc_errors"),
        ("magic_drc_errors", "magic__drc_error__count"),
        ("lvs_errors", "design__lvs_error__count"),
        ("antenna_violations", "route__antenna_violation__count"),
    )
    for result_key, raw_key in metric_cross_checks:
        require(physical_result[result_key] == raw_metrics[raw_key], f"raw metric disagrees: {result_key}")
    require(
        float(selected_metrics["synthesis_mapped_cell_count"])
        == physical_result["synthesis_mapped_cells"],
        "selected synthesis cell count disagrees",
    )
    require(
        float(selected_metrics["timing_repair_buffer_count"])
        == physical_result["timing_repair_buffers"],
        "selected timing-repair buffer count disagrees",
    )
    require(
        float(selected_metrics["clock_buffer_count"]) == physical_result["clock_buffers"],
        "selected clock buffer count disagrees",
    )
    require(
        physical_result["synthesis_mapped_cells"]
        + physical_result["timing_repair_buffers"]
        + physical_result["clock_buffers"]
        == physical_result["final_standard_cells"],
        "mapped-cell and inserted-buffer counts do not explain the placed-cell total",
    )
    require(commit_id["commit"] == physical["source_commit"], "source commit records disagree")
    require(git_blob_sha1(source_bytes) == expected_blob, "archived M0 RTL differs from its Git blob ID")
    require(archived_source["path"] == source_path.name, "archived M0 RTL path record disagrees")
    require(archived_source["git_blob_sha1"] == expected_blob, "archived M0 RTL blob records disagree")
    require(
        hashlib.sha256(source_bytes).hexdigest() == archived_source["sha256"],
        "archived M0 RTL differs from its recorded SHA-256",
    )
    require(
        comparison["equivalent_except_timestamps"] is True
        and not comparison["non_timestamp_record_differences"],
        "E0006 and E0010 GDS records differ beyond timestamps",
    )

    gate_root = ET.parse(E0010 / "gatelevel-results.xml").getroot()
    gate_cases = gate_root.findall(".//testcase")
    require(len(gate_cases) == physical["gate_level"]["tests_passed"] == 2, "gate-level test counts disagree")
    require(not gate_root.findall(".//failure") and not gate_root.findall(".//error"), "gate-level JUnit contains a failure")

    precheck_root = ET.parse(E0010 / "precheck-results.xml").getroot()
    precheck_cases = precheck_root.findall(".//testcase")
    require(len(precheck_cases) == physical["precheck"]["checks_passed"] == 9, "precheck counts disagree")
    require(not precheck_root.findall(".//failure") and not precheck_root.findall(".//error"), "precheck JUnit contains a failure")

    qualified = lock["official_cmos5l_qualification"]
    resolved = physical["resolved_environment"]
    for lock_key, result_key in (
        ("outer_action_commit", "tt_gds_action_commit"),
        ("support_tools_commit", "tt_support_tools_commit"),
        ("librelane", "flow_version"),
        ("pdk", "pdk"),
        ("pdk_commit", "pdk_commit"),
    ):
        require(qualified[lock_key] == resolved[result_key], f"tool lock differs from E0010: {lock_key}")

    anchors = {
        "state": line_number(source_lines, "reg [7:0] count;"),
        "edge": line_number(source_lines, "always @(posedge clk)"),
        "reset": line_number(source_lines, "if (!rst_n)"),
        "increment": line_number(source_lines, "count <= count + 8'h01;"),
        "output": line_number(source_lines, "assign uo_out = count;"),
    }
    return {
        "fast": fast,
        "physical": physical,
        "comparison": comparison,
        "gate_cases": [case.attrib["name"] for case in gate_cases],
        "precheck_count": len(precheck_cases),
        "anchors": anchors,
        "source_blob": expected_blob,
    }


def print_header(model: dict) -> None:
    physical = model["physical"]
    print("M0 GUIDED WALKTHROUGH - from Verilog to GDS")
    print("=" * 49)
    print("Purpose: inspect one real, qualified result and learn what each stage establishes.")
    print("This command is read-only. Running it does NOT mark the fluency checkpoint complete.")
    print(f"Physical snapshot: E0010, source {physical['source_commit']}")
    print(f"Archived RTL Git blob: {model['source_blob']}")


def print_rtl(model: dict) -> None:
    anchors = model["anchors"]
    path = "evidence/E0010-pinned-cmos5l-run/source-project.v"
    print("\n1. RTL - the hardware behaviour we asked for")
    print("-" * 47)
    print(f"State lives in the 8-bit 'count' register: {path}:{anchors['state']}")
    print(f"It may change only at a rising clock edge: {path}:{anchors['edge']}")
    print(f"Reset is checked first: {path}:{anchors['reset']}")
    print(f"Otherwise enable advances it by one: {path}:{anchors['increment']}")
    print(f"The register is exposed on the output pins: {path}:{anchors['output']}")
    print("Mental model: this is a tiny state machine. The clock edge is the moment it may act.")
    print("\nTranslate the short signal names:")
    print("  clk   clock: the repeating timing pulse; M0 acts only on its rising edge")
    print("  rst_n reset-not: 0 means reset now; 1 means normal operation")
    print("  ena   enable: 1 means count; 0 means pause and remember")
    print("  00    hexadecimal zero: the eight output bits are all zero")
    print("\nWorked row: rst_n=1, ena=0, before=00, after=00.")
    print("Why: reset is not active, and enable says pause, so the register remembers 00.")
    print("Practice: restate that 'why' sentence in your own words; terminology is optional.")
    print("Next prediction: count=0x2A and ena=0 at a rising edge -> count remains 0x2A.")


def print_verification(model: dict) -> None:
    fast = model["fast"]
    formal = fast["formal"]
    print("\n2. Fast verification - ask different kinds of questions")
    print("-" * 58)
    print(
        "Simulation: Icarus and Verilator each passed "
        f"{fast['rtl']['icarus_tests_passed']} tests over "
        f"{fast['rtl']['simulated_time_per_engine_ns']:,} simulated ns."
    )
    print(f"  Tests: {', '.join(fast['rtl']['tests'])}")
    print("  Establishes: the chosen journeys produced the expected public-pin values.")
    print("  Limit: untested journeys may still contain bugs; both simulators share one oracle.")
    print(f"Formal: {formal['proof']}; the wrap witness reaches FF/00 at steps {formal['cover_ff_step']}/{formal['cover_wrap_step']}.")
    print(f"  Falsification check: the +2 mutant is caught at step {formal['mutant_detected_step']}.")
    print("  Establishes: the written digital assertions hold for every behaviour allowed by the model.")
    print("  Limit: formal cannot prove a rule nobody wrote, or analog/fabricated behaviour.")
    print("  Vocabulary: an assertion is a rule; an assumption limits allowed inputs;")
    print("  a cover asks for one reachable example; a counterexample shows a rule breaking.")
    print("  M0 safety used zero input assumptions; only the readable wrap cover constrained reset/enable.")
    print(
        f"Generic synthesis: PASS, {fast['generic_synthesis']['cells']} abstract cells; "
        "physical fit was explicitly NOT evaluated."
    )


def print_physical(model: dict) -> None:
    result = model["physical"]
    physical = result["physical_result"]
    environment = result["resolved_environment"]
    comparison = model["comparison"]
    print("\n3. Physical qualification - turn logic into a layout")
    print("-" * 53)
    print(
        f"Technology mapping: {physical['synthesis_mapped_cells']} IHP-mapped cells, "
        f"{physical['synthesis_mapped_area_um2']:.4f} um^2."
    )
    print(
        f"Placed result: {physical['final_standard_cells']} standard cells, "
        f"{physical['instance_utilization_percent']:.6f}% utilization."
    )
    print(
        f"Why 80 instead of 58? The flow inserted {physical['timing_repair_buffers']} timing-repair "
        f"and {physical['clock_buffers']} clock buffers."
    )
    print(
        f"Timing at the {physical['clock_target_ns']} ns target: "
        f"setup slack +{physical['worst_setup_slack_ns']:.6f} ns; "
        f"hold slack +{physical['worst_hold_slack_ns']:.6f} ns."
    )
    print("  Positive slack means the analyzed paths met this target and these modeled corners.")
    print("  It is not a measurement of the design's maximum frequency.")
    print(
        "Physical checks: route DRC, Magic DRC, LVS, antenna, setup and hold "
        "all record zero violations."
    )
    print(f"Tiny Tapeout precheck: {model['precheck_count']}/9 checks passed.")
    print(f"Gate-level simulation: {len(model['gate_cases'])}/2 tests passed on the generated cell netlist.")
    print(
        f"GDS: {physical['gds_record_count']:,} records; exact SHA-256 "
        f"{physical['gds_sha256']}"
    )
    print(
        "Reproduction: E0006 versus E0010 differs in "
        f"{comparison['different_bytes']} timestamp bytes only; no geometry record differs."
    )
    print("Exact tool batch:")
    print(f"  Tiny Tapeout GDS action {environment['tt_gds_action_commit']}")
    print(f"  support-tools {environment['tt_support_tools_commit']}")
    print(f"  LibreLane {environment['flow_version']}")
    print(f"  IHP Open PDK {environment['pdk_commit']}")


def print_claims(model: dict) -> None:
    print("\n4. Claim ladder - a pass answers one bounded question")
    print("-" * 56)
    rows = (
        ("Simulation", "Did selected input journeys behave as expected?"),
        ("Formal", "Can any modeled trace break the assertions we wrote?"),
        ("Generic synthesis", "Can the RTL become an abstract gate network?"),
        ("Place and route", "Can mapped cells be positioned and connected in the tile?"),
        ("Timing analysis", "Do modeled signal paths meet the 20 ns target?"),
        ("DRC/LVS/precheck", "Does the layout pass the recorded geometry, connectivity and submission rules?"),
        ("Gate-level test", "Does the generated functional netlist retain the tested pin behaviour?"),
        ("GDS", "What exact manufacturing-geometry file did the flow emit?"),
    )
    for stage, question in rows:
        print(f"{stage:19} {question}")
    print("\nStill NOT proved: fabricated-silicon behaviour, analog correctness, Fmax, or a protocol VM.")
    print("\nTEACH-BACK START")
    print("In your own words: why is generic Yosys synthesis insufficient to prove physical fit,")
    print("and which E0010 stages provide the missing evidence?")
    print("Useful shape: 'Generic synthesis establishes ____. E0010 additionally establishes ____.'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--section",
        choices=("all", "rtl", "verification", "physical", "claims"),
        default="all",
        help="show one part of the walkthrough (default: all)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="validate the retained source/evidence relationships without printing the lesson",
    )
    args = parser.parse_args()
    model = load_model()
    if args.verify:
        print("PASS: archived M0 RTL, fast evidence, physical evidence and tool lock agree.")
        print("LIMIT: evidence consistency cannot demonstrate owner fluency or fabricated-silicon behaviour.")
        return

    print_header(model)
    sections = {
        "rtl": print_rtl,
        "verification": print_verification,
        "physical": print_physical,
        "claims": print_claims,
    }
    selected = sections if args.section == "all" else {args.section: sections[args.section]}
    for printer in selected.values():
        printer(model)


if __name__ == "__main__":
    main()
