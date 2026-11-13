# SPDX-License-Identifier: Apache-2.0
"""Stage E0030-identical physical candidates and reject mismatched run evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
E0030 = ROOT / "evidence/E0030-timed-gpio-comparison/comparison"
BASE_CONFIG_PATH = "experiments/physical/d34-config.json"
sys.path.insert(0, str(ROOT / "experiments/spi_phase"))
from build_timed_gpio import build
from build_variants import FILES

PUBLIC_TESTS = {
    "public_pin_reload_changes_observable_program",
    "k_input_wait_public_program_event_timeout_and_reload",
    "k_bounded_loop_public_program_counts",
    "k_shift_8_public_payload_both_orders",
    "uart_tx_8n1_public_pin_oracle",
    "uart_rx_host_service_last_safe_edge",
    "uart_rx_host_service_fault_abort_quarantine",
    "uart_rx_host_service_late_read_counterexample",
    "uart_rx_public_bounded_last_byte_delivery",
    "uart_rx_public_framing_and_bounded_timeouts",
    "uart_rx_public_disable_reset_abort_then_reload",
    "timed_public_programs",
}


PUBLIC_TEST_MODULES = {
    name: ("test_uart_rx_public" if name.startswith("uart_rx_") else
           "test_spi_timed_gpio" if name == "timed_public_programs" else "test")
    for name in PUBLIC_TESTS
}
EXCLUDED_TESTS = {
    ("test", name) for name in (
        "invalid_length_never_releases_engine", "synchronized_input_wait_event_and_timeout",
        "loop_target_overflow_faults_without_alias", "timed_shift_burst_invalid_freeze_and_reset",
        "timed_shift_burst_trace_matches_semantic_model", "shift_trace_matches_semantic_model",
        "shift_invalid_partial_and_reset_fail_closed", "randomized_trace_matches_reviewed_model",
        "invalid_encoding_and_out_of_range_fail_closed")
} | {("test_spi_timed_gpio", "timed_instruction_and_abort_controls")}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def text_digest(path):
    return hashlib.sha256(Path(path).read_text(encoding="utf-8").encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def candidate_lock():
    return read_json(ROOT / "tools/workbench/toolchain.lock.json")["official_cmos5l_8x4"]


def baseline_config():
    """Return the immutable D34 input independently of future production setup."""
    path = ROOT / BASE_CONFIG_PATH
    require(digest(path) == candidate_lock()["config_sha256_lf"],
            "archived D34 physical configuration changed")
    return path


def expected_sources(variant):
    return read_json(E0030 / "variants/source-manifest.json")[variant]["source_sha256"]


def verify_sources(directory, variant):
    actual = {name: digest(Path(directory) / name) for name in FILES}
    require(actual == expected_sources(variant), "candidate RTL differs from E0030")
    return actual


def prepare(args):
    out = args.output.resolve()
    require(out.is_relative_to((ROOT / "build").resolve()), "output must be within build/")
    require(not out.exists(), "new output directory required; retain previous attempts")
    lock = candidate_lock()
    info = (ROOT / "info.yaml").read_text(encoding="utf-8")
    require(re.search(r'^\s{2}tiles: "8x4"\s', info, re.M), "metadata is not 8x4")
    require(re.search(r"^\s{2}clock_hz:\s+50000000\s", info, re.M), "metadata clock drift")
    config = baseline_config()
    if args.stage_ci:
        require(os.getenv("GITHUB_ACTIONS") == "true", "in-place staging is CI-only")
        require(Path(os.environ["GITHUB_WORKSPACE"]).resolve() == ROOT,
                "CI workspace differs from this checkout")
        dirty = subprocess.check_output(["git", "status", "--porcelain",
                                         "--untracked-files=no"], cwd=ROOT, text=True)
        require(not dirty, "tracked checkout must be clean before CI staging")

    build(out / "variants")
    sources = out / "variants" / args.variant / "src"
    hashes = verify_sources(sources, args.variant)
    shutil.copyfile(config, out / "config.json")
    record = {
        "schema": "protocol-emulator-physical-candidate-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "variant": args.variant,
        "workflow_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_evidence": "E0030",
        "program_words": 8 if args.variant == "P" else 10,
        "source_sha256": hashes,
        "config_sha256_lf": digest(config),
        "config_source_path": BASE_CONFIG_PATH,
        "metadata_sha256_lf": text_digest(ROOT / "info.yaml"),
        "flow_lock": lock,
        "provenance_sha256_lf": {name: text_digest(ROOT / name) for name in (
            "tools/physical_candidate.py", BASE_CONFIG_PATH, ".github/workflows/gds-g1.yaml",
            "test/Makefile", "test/tb.v", "test/test.py", "test/test_uart_rx_public.py",
            "test/test_spi_timed_gpio.py", "experiments/spi_phase/build_timed_gpio.py",
            "experiments/spi_phase/build_variants.py", "experiments/spi_phase/timed_gpio_programs.py",
            "tools/spi_four_mode_oracle.py", "docs/specs/g1-cmos5l-physical-comparison.md")},
        "staged_in_ci": bool(args.stage_ci),
        "public_test_names": sorted(PUBLIC_TESTS),
        "source_note": "Workflow revision plus staged hashes identify this experimental chip.",
    }
    write_json(out / "inputs.json", record)
    if args.stage_ci:
        shutil.copyfile(out / "config.json", ROOT / "src/config.json")
        for name in FILES:
            shutil.copyfile(sources / name, ROOT / "src" / name)
        verify_sources(ROOT / "src", args.variant)
    print(f"PASS: {args.variant} source identities match E0030; inputs: {out / 'inputs.json'}")


SIGNOFF_CORNERS = ("nom_fast_1p32V_m40C", "nom_slow_1p08V_125C", "nom_typ_1p20V_25C")


def inspect_physical_metrics(metrics):
    """Fail closed on final physical counts and setup/hold at all frozen corners."""
    zero_counts = (
        "route__drc_errors", "route__antenna_violation__count",
        "antenna__violating__nets", "antenna__violating__pins",
        "magic__drc_error__count", "design__lvs_error__count",
        "design__power_grid_violation__count",
    )
    electrical = tuple(f"design__max_{kind}_violation__count"
                       for kind in ("fanout", "cap", "slew"))
    slacks = ("timing__setup__ws", "timing__hold__ws")
    checked, errors = {}, []
    requirements = [(key, "zero") for key in zero_counts]
    for corner in (None, *SIGNOFF_CORNERS):
        suffix = "" if corner is None else f"__corner:{corner}"
        requirements.extend((key + suffix, "zero") for key in electrical)
        requirements.extend((key + suffix, "nonnegative") for key in slacks)
    for key, condition in requirements:
        value = metrics.get(key)
        valid = (isinstance(value, (int, float)) and not isinstance(value, bool)
                 and math.isfinite(value))
        checked[key] = value if valid else None
        if not valid:
            errors.append(f"{key}: missing or non-finite numeric result")
        elif (condition == "zero" and value != 0) or (condition == "nonnegative" and value < 0):
            errors.append(f"{key}: {value} violates {condition} requirement")
    return {"status": "PASS" if not errors else "FAIL", "checked": checked, "errors": errors}


def verify_run_configuration(resolved, lock):
    for name, expected in lock["physical_constraints"].items():
        require(resolved.get(name) == expected, f"resolved {name} differs")
    die = resolved["DIE_AREA"]
    if isinstance(die, str):
        die = die.split()
    require([float(n) for n in die] == lock["die_area_um"], "resolved die area differs")
    require(resolved["DEFAULT_CORNER"] == lock["default_corner"], "default corner drift")
    require(resolved["RT_MAX_LAYER"] == "Metal4", "routing layer differs")
    require(tuple(resolved["STA_CORNERS"]) == SIGNOFF_CORNERS, "signoff corner set drift")


def check_run(args):
    run = args.run.resolve()
    lock = candidate_lock()
    sources = verify_sources(ROOT / "src", args.variant)
    pdk = read_json(run / "pdk.json")
    require(pdk["FLOW_VERSION"] == lock["librelane"], "LibreLane version drift")
    require(pdk["PDK"] == lock["pdk"] and pdk["PDK_VERSION"] == lock["pdk_commit"],
            "PDK identity drift")
    require(pdk["PDK_SOURCE"] == lock["pdk_source"], "PDK source drift")
    resolved = read_json(run / "resolved.json")
    verify_run_configuration(resolved, lock)
    require(text_digest(ROOT / "src/config.json") == lock["config_sha256_lf"],
            "shared configuration changed during flow")
    support_commit = subprocess.check_output(["git", "-C", str(ROOT / "tt"),
                                              "rev-parse", "HEAD"], text=True).strip()
    require(support_commit == lock["support_tools_commit"], "support-tools identity drift")
    netlist = ROOT / "tt_submission/tt_um_khangelani_protocol_emulator.v"
    require(netlist.is_file(), "submission netlist missing")
    require("sg13cmos5l_" in netlist.read_text(encoding="utf-8"), "not a CMOS5L netlist")
    metrics_path = run / "final/metrics.json"
    metrics_review = inspect_physical_metrics(read_json(metrics_path))
    record = {
        "status": ("INPUT_IDENTITIES_AND_PHYSICAL_METRICS_VERIFIED_PRECHECK_PENDING"
                   if metrics_review["status"] == "PASS" else "PHYSICAL_METRICS_FAILED"),
        "physical_metrics": metrics_review,
        "metrics_sha256": digest(metrics_path),
        "variant": args.variant, "source_sha256": sources, "pdk": pdk,
        "netlist_sha256": digest(netlist),
        "resolved_config_sha256": digest(run / "resolved.json"),
        "comparison_configuration": {key: resolved.get(key) for key in (
            "CLOCK_PERIOD", "PL_TARGET_DENSITY_PCT", "PL_RESIZER_HOLD_SLACK_MARGIN",
            "GRT_RESIZER_HOLD_SLACK_MARGIN", "DIE_AREA", "DEFAULT_CORNER", "STA_CORNERS",
            "STD_CELL_LIBRARY", "CELL_LIBS", "EXTRA_LIBS", "RT_MAX_LAYER",
            "MAX_FANOUT_CONSTRAINT", "CTS_SINK_CLUSTERING_SIZE",
            "CTS_DISTANCE_BETWEEN_BUFFERS", "RANDOM_GLB_PLACEMENT",
            "PL_RANDOM_SEED", "PNR_SDC_FILE", "SIGNOFF_SDC_FILE")},
    }
    write_json(args.output, record)
    require(metrics_review["status"] == "PASS",
            "physical metrics failed: " + "; ".join(metrics_review["errors"]))
    print("PASS: physical inputs, timing and violation counts; precheck and netlist tests remain separate")


def check_tests(args):
    root = ET.parse(args.junit).getroot()
    cases = root.findall(".//testcase")
    identities = [(case.attrib.get("classname"), case.attrib["name"]) for case in cases]
    required = {(module, name) for name, module in PUBLIC_TEST_MODULES.items()}
    require(len(identities) == len(set(identities)), "duplicate test identity")
    require(required <= set(identities), "missing required public test group")
    selected, excluded = [], []
    for identity, case in zip(identities, cases):
        require(case.find("failure") is None and case.find("error") is None,
                "failed public test or excluded test")
        if identity in required:
            require(case.find("skipped") is None, "failed or skipped public test")
            selected.append(case)
        else:
            require(identity in EXCLUDED_TESTS and case.find("skipped") is not None,
                    "unexpected test outside the declared public selection")
            excluded.append(".".join(identity))
    records = [json.loads(line) for line in args.records.read_text(encoding="utf-8").splitlines()]
    transfers = [row for row in records if "trace_sha256" in row]
    require(len(records) == len(transfers) == 1052, "missing or extra SPI transfers")
    require(sum(row["accepted"] for row in transfers) == 1048, "SPI acceptance count differs")
    old = E0030 / args.variant / "public-icarus/records/cases.jsonl.gz"
    reference = [json.loads(line) for line in gzip.decompress(old.read_bytes()).decode().splitlines()]
    reference = [row for row in reference if "trace_sha256" in row]
    require(transfers == reference, "public SPI records differ from retained E0030 expectations")
    result = {
        "status": "PASS", "variant": args.variant, "public_test_groups": len(selected),
        "excluded_discovered_tests": excluded,
        "spi_transfers": len(transfers), "positive": 1048, "expected_negative_controls": 4,
        "reference_records_identical": True, "junit_sha256": digest(args.junit),
        "records_sha256": digest(args.records), "netlist_sha256": None,
        "evidence_kind": "RTL_WITHOUT_DIRECT_ENGINE",
    }
    if args.require_netlist:
        netlist = ROOT / "test/gate_level_netlist.v"
        submission = ROOT / "tt_submission/tt_um_khangelani_protocol_emulator.v"
        require(digest(netlist) == digest(submission), "tested/submitted netlist mismatch")
        require("sg13cmos5l_" in netlist.read_text(encoding="utf-8"), "not a CMOS5L netlist")
        result.update(netlist_sha256=digest(netlist), evidence_kind="FUNCTIONAL_ZERO_DELAY_NETLIST")
    write_json(args.output, result)
    print(f"PASS: 12 public groups and 1052 unchanged SPI records ({result['evidence_kind']})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    p = actions.add_parser("prepare")
    p.add_argument("--variant", choices=("P", "compact10"), required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--stage-ci", action="store_true")
    p.set_defaults(function=prepare)
    p = actions.add_parser("check-run")
    p.add_argument("--variant", choices=("P", "compact10"), required=True)
    p.add_argument("--run", type=Path, default=ROOT / "runs/wokwi")
    p.add_argument("--output", type=Path, required=True)
    p.set_defaults(function=check_run)
    p = actions.add_parser("check-tests")
    p.add_argument("--variant", choices=("P", "compact10"), required=True)
    p.add_argument("--junit", type=Path, required=True)
    p.add_argument("--records", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--require-netlist", action="store_true")
    p.set_defaults(function=check_tests)
    args = parser.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
