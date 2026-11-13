# SPDX-License-Identifier: Apache-2.0
"""Stage the identified G2 chip and reject incomplete physical evidence."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments/i2c"))
from tools import physical_candidate as common
from build_general import build
import store_lanes
import shared_read

EVIDENCE = ROOT / "evidence/E0036-g2-store-and-ci"
MANIFEST = ROOT / "evidence/E0035-general-i2c/sources/current/source-manifest.json"
PUBLIC_TEST_MODULES = dict(common.PUBLIC_TEST_MODULES, **{
    "complete_i2c_transactions": "test_i2c_general_public",
    "public_store_banks_lengths_and_reset": "test_general_boundaries",
    "public_pc_branch_and_skip_boundaries": "test_general_boundaries",
    "public_branch_abandons_partial_byte_and_loop": "test_general_boundaries",
    "public_open_drain_and_alternate_payload": "test_general_boundaries",
    "public_i2c_abort_and_reload": "test_i2c_abort_public",
})
require = common.require
digest = common.digest
read_json = common.read_json
write_json = common.write_json


def candidate_manifest(variant):
    if variant == "od128-shared":
        return read_json(shared_read.MANIFEST)["od128"]
    if variant == "od128-lanes":
        return read_json(store_lanes.MANIFEST)["od128"]
    return read_json(MANIFEST)[variant]


def verify_sources(directory, variant):
    expected = candidate_manifest(variant)["source_sha256"]
    actual = {name: digest(Path(directory) / name) for name in expected}
    require(actual == expected, "G2 source differs from the retained candidate: " + variant)
    return actual


def prepare(args):
    out = args.output.resolve()
    require(out.is_relative_to((ROOT / "build").resolve()), "output must be within build/")
    require(not out.exists(), "new output required; preserve earlier attempts")
    lock = common.candidate_lock()
    info = (ROOT / "info.yaml").read_text(encoding="utf-8")
    require(re.search(r'^\s{2}tiles: "8x4"\s', info, re.M), "metadata is not 8x4")
    require(re.search(r"^\s{2}clock_hz:\s+50000000\s", info, re.M), "metadata clock drift")
    config = common.baseline_config()
    ci = read_json(EVIDENCE / "ci/verification.json")
    require(ci["status"] == "PASS_AUDITED_G2_CI", "current candidate CI audit missing")
    explicit_lanes = args.variant == "od128-lanes"
    shared = args.variant == "od128-shared"
    implementation = shared_read if shared else store_lanes
    qualification = implementation.EVIDENCE / "qualification.json"
    if explicit_lanes or shared:
        qualified = read_json(qualification)
        expected_status = "PASS_SHARED_CANDIDATE_RTL_FORMAL" if shared else "PASS_LANES_CANDIDATE_RTL_FORMAL"
        require(qualified["status"] == expected_status, "implementation RTL/formal qualification missing")
        require(qualified["source_sha256"] == candidate_manifest(args.variant)["source_sha256"],
                "implementation qualification source mismatch")
    if args.stage_ci:
        require(os.getenv("GITHUB_ACTIONS") == "true", "in-place staging is CI-only")
        require(Path(os.environ["GITHUB_WORKSPACE"]).resolve() == ROOT,
                "CI workspace differs from checkout")
        dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"],
                                        cwd=ROOT, text=True)
        require(not dirty, "tracked checkout must be clean before CI staging")
    (implementation.build if explicit_lanes or shared else build)(out / "variants")
    sources = out / "variants" / ("od128" if explicit_lanes or shared else args.variant) / "src"
    hashes = verify_sources(sources, args.variant)
    shutil.copyfile(config, out / "config.json")
    record = {
        "schema": "protocol-emulator-g2-physical-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(), "variant": args.variant,
        "workflow_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                            cwd=ROOT, text=True).strip(),
        "source_evidence": "E0038" if shared else "E0037" if explicit_lanes else "E0035",
        "ci_audit_sha256": digest(EVIDENCE / "ci/verification.json"),
        "program_words": candidate_manifest(args.variant)["capacity"],
        "source_sha256": hashes, "flow_lock": lock,
        "config_sha256_lf": digest(config), "config_source_path": common.BASE_CONFIG_PATH,
        "metadata_sha256_lf": common.text_digest(ROOT / "info.yaml"),
        "provenance_sha256_lf": {name: common.text_digest(ROOT / name) for name in (
            "tools/physical_g2.py", "tools/physical_candidate.py", common.BASE_CONFIG_PATH, ".github/workflows/gds-g2.yaml",
            "test/Makefile", "test/tb.v", "test/test.py", "test/test_uart_rx_public.py",
            "test/test_spi_timed_gpio.py", "test/test_i2c_general_public.py",
            "test/test_general_boundaries.py", "test/test_i2c_abort_public.py",
            "experiments/i2c/build_general.py", "experiments/i2c/general_programs.py",
            "experiments/i2c/public_bus.py", "experiments/i2c/target.py",
            "tools/i2c_oracle.py", "tools/spi_four_mode_oracle.py",
            "docs/specs/g2-cmos5l-qualification.md")},
        "staged_in_ci": bool(args.stage_ci),
        "public_test_names": sorted(PUBLIC_TEST_MODULES) if args.variant in ("od128", "od128-lanes", "od128-shared") else [],
        "scope": "Experimental complete chip; production promotion remains a separate decision",
    }
    if explicit_lanes:
        record["implementation_qualification_sha256"] = digest(qualification)
        for path in (store_lanes.MANIFEST, qualification, ROOT / "experiments/i2c/store_lanes.py",
                     ROOT / "experiments/i2c/run_store_lanes_gate.py",
                     ROOT / "docs/decisions/0038-explicit-store-lanes-after-routing-failure.md"):
            record["provenance_sha256_lf"][path.relative_to(ROOT).as_posix()] = common.text_digest(path)
    if shared:
        record["implementation_qualification_sha256"] = digest(qualification)
        for path in (shared_read.MANIFEST, qualification, ROOT / "experiments/i2c/shared_read.py",
                     ROOT / "experiments/i2c/run_shared_read_gate.py", ROOT / "experiments/i2c/run_shared_read_proof.py",
                     ROOT / "experiments/i2c/run_shared_read_controls.py", ROOT / "test/test_shared_read_controls.py",
                     ROOT / "docs/decisions/0039-shared-program-read.md"):
            record["provenance_sha256_lf"][path.relative_to(ROOT).as_posix()] = common.text_digest(path)
    write_json(out / "inputs.json", record)
    if args.stage_ci:
        shutil.copyfile(out / "config.json", ROOT / "src/config.json")
        for name in hashes:
            shutil.copyfile(sources / name, ROOT / "src" / name)
        verify_sources(ROOT / "src", args.variant)
    print(f"PASS: {args.variant} generated identities match {record['source_evidence']}")


def check_run(args):
    run = args.run.resolve()
    lock = common.candidate_lock()
    sources = verify_sources(ROOT / "src", args.variant)
    pdk = read_json(run / "pdk.json")
    require(pdk["FLOW_VERSION"] == lock["librelane"], "LibreLane version drift")
    require(pdk["PDK"] == lock["pdk"] and pdk["PDK_VERSION"] == lock["pdk_commit"],
            "PDK identity drift")
    require(pdk["PDK_SOURCE"] == lock["pdk_source"], "PDK source drift")
    resolved = read_json(run / "resolved.json")
    common.verify_run_configuration(resolved, lock)
    require(common.text_digest(ROOT / "src/config.json") == lock["config_sha256_lf"],
            "physical configuration drift")
    support = subprocess.check_output(["git", "-C", str(ROOT / "tt"), "rev-parse", "HEAD"],
                                      text=True).strip()
    require(support == lock["support_tools_commit"], "support-tools identity drift")
    netlist = ROOT / "tt_submission/tt_um_khangelani_protocol_emulator.v"
    require(netlist.is_file() and "sg13cmos5l_" in netlist.read_text(encoding="utf-8"),
            "actual CMOS5L submission netlist missing")
    metrics = run / "final/metrics.json"
    review = common.inspect_physical_metrics(read_json(metrics))
    write_json(args.output, {
        "status": "PASS_PHYSICAL_METRICS_PRECHECK_AND_NETLIST_PENDING" if review["status"] == "PASS"
                  else "PHYSICAL_METRICS_FAILED",
        "variant": args.variant, "source_sha256": sources, "pdk": pdk,
        "physical_metrics": review, "metrics_sha256": digest(metrics),
        "resolved_config_sha256": digest(run / "resolved.json"), "netlist_sha256": digest(netlist),
        "comparison_configuration": {key: resolved.get(key) for key in (
            "CLOCK_PERIOD", "PL_TARGET_DENSITY_PCT", "PL_RESIZER_HOLD_SLACK_MARGIN",
            "GRT_RESIZER_HOLD_SLACK_MARGIN", "DIE_AREA", "DEFAULT_CORNER", "STA_CORNERS",
            "STD_CELL_LIBRARY", "CELL_LIBS", "EXTRA_LIBS", "RT_MAX_LAYER",
            "MAX_FANOUT_CONSTRAINT", "CTS_SINK_CLUSTERING_SIZE", "CTS_DISTANCE_BETWEEN_BUFFERS",
            "RANDOM_GLB_PLACEMENT", "PL_RANDOM_SEED", "PNR_SDC_FILE", "SIGNOFF_SDC_FILE")},
    })
    require(review["status"] == "PASS", "physical metrics failed: " + "; ".join(review["errors"]))
    print("PASS: matching physical inputs and all required routed metrics")


def records(path):
    data = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text(encoding="utf-8")
    return [json.loads(line) for line in data.splitlines()]


def check_public_records(directory):
    """Check reference observations without labelling the simulation harness."""
    references = {
        "spi/cases.jsonl": ("architecture/combined/icarus/records/cases.jsonl.gz", 1052),
        "i2c/cases.jsonl": ("od128/protocols/icarus/records/cases.jsonl.gz", 1160),
        "i2c/boundaries.jsonl": ("architecture/boundaries/od128-icarus/records/boundaries.jsonl.gz", 4),
        "i2c/aborts.jsonl": ("architecture/aborts/od128-icarus/records/aborts.jsonl.gz", 36),
    }
    checked = {}
    for name, (reference, count) in references.items():
        path = directory / name
        observed = records(path)
        # The SPI runner also retains architectural records; select wire transfers exactly as in G1.
        if name.startswith("spi/"):
            observed = [row for row in observed if "trace_sha256" in row]
        expected = records(EVIDENCE / "ci" / reference)
        if name.startswith("spi/"):
            expected = [row for row in expected if "trace_sha256" in row]
        require(len(observed) == len(expected) == count, f"missing or extra records: {name}")
        require(observed == expected, f"public records differ from audited RTL: {name}")
        checked[name] = {"count": count, "sha256": digest(path), "reference_identical": True}
    return checked


def check_tests(args):
    cases = ET.parse(args.junit).getroot().findall(".//testcase")
    identities = [(case.attrib.get("classname"), case.attrib["name"]) for case in cases]
    required = {(module, name) for name, module in PUBLIC_TEST_MODULES.items()}
    require(len(identities) == len(set(identities)), "duplicate test identity")
    require(required <= set(identities), "missing required public test group")
    excluded = []
    for identity, case in zip(identities, cases):
        require(case.find("failure") is None and case.find("error") is None, "failed public test")
        if identity in required:
            require(case.find("skipped") is None, "required public test skipped")
        else:
            require(identity in common.EXCLUDED_TESTS and case.find("skipped") is not None,
                    "unexpected test outside the declared public selection")
            excluded.append(".".join(identity))
    checked = check_public_records(args.records)
    result = {"status": "PASS", "variant": "od128", "public_test_groups": len(required),
              "excluded_discovered_tests": excluded, "records": checked,
              "junit_sha256": digest(args.junit), "netlist_sha256": None,
              "evidence_kind": "RTL_WITHOUT_DIRECT_ENGINE"}
    if args.require_netlist:
        netlist = ROOT / "test/gate_level_netlist.v"
        submission = ROOT / "tt_submission/tt_um_khangelani_protocol_emulator.v"
        require(digest(netlist) == digest(submission), "tested/submitted netlist mismatch")
        require("sg13cmos5l_" in netlist.read_text(encoding="utf-8"), "not a CMOS5L netlist")
        result.update(netlist_sha256=digest(netlist), evidence_kind="FUNCTIONAL_ZERO_DELAY_NETLIST")
    write_json(args.output, result)
    print("PASS: 18 public groups and all audited protocol/boundary/abort records")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    actions = p.add_subparsers(dest="action", required=True)
    for action in ("prepare", "check-run", "check-tests"):
        sub = actions.add_parser(action)
        sub.add_argument("--output", type=Path, required=True)
        if action != "check-tests":
            sub.add_argument("--variant", choices=("od128", "literal255", "od128-lanes", "od128-shared"), required=True)
        if action == "prepare":
            sub.add_argument("--stage-ci", action="store_true")
        elif action == "check-run":
            sub.add_argument("--run", type=Path, default=ROOT / "runs/wokwi")
        else:
            sub.add_argument("--junit", type=Path, required=True)
            sub.add_argument("--records", type=Path, required=True)
            sub.add_argument("--require-netlist", action="store_true")
        sub.set_defaults(function={"prepare": prepare, "check-run": check_run, "check-tests": check_tests}[action])
    args = p.parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
