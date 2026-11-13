# SPDX-License-Identifier: Apache-2.0
"""Audit original G2 physical archives and bind their three consumer jobs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import physical_candidate as common, physical_g2
from tools.physical_runtime import inspect_runtime, inspect_consumed_artifact

require = common.require
TOP = "tt_um_khangelani_protocol_emulator"
REQUIRED_ARCHIVES = {"GDS_logs", "tt_submission", "g2-physical-candidate",
                     "precheck_reports", "gatelevel_test_results", "g2-netlist-check"}
PRECHECK_NAMES = {
    "KLayout pin label overlapping drawing", "KLayout SG13CMOS5L DRC",
    "KLayout zero area", "KLayout Checks", "Pin check", "Boundary check",
    "Layer check", "Cell name check", "Analog pin check", "Verilog syntax check",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def frozen(source, name):
    return subprocess.check_output(["git", "show", source + ":" + name], cwd=ROOT)


class Archive:
    def __init__(self, directory, metadata, run):
        self.metadata = metadata
        require(metadata["workflow_run"]["id"] == run["id"], "archive belongs to another run")
        require(metadata["workflow_run"]["head_sha"] == run["head_sha"], "archive source mismatch")
        path = directory / (str(metadata["id"]) + ".zip")
        require(path.stat().st_size == metadata["size_in_bytes"], "archive size mismatch")
        self.digest = common.digest(path)
        require(metadata["digest"] == "sha256:" + self.digest, "archive digest mismatch")
        self.file = zipfile.ZipFile(path)
        names = self.file.namelist()
        require(len(names) == len(set(names)), "duplicate archive member")

    def bytes(self, name):
        return self.file.read(name)

    def json(self, name):
        return json.loads(self.bytes(name))


def inspect_precheck(raw):
    root = ET.fromstring(raw)
    cases = root.findall(".//testcase")
    names = [case.get("name") for case in cases]
    require(len(names) == len(set(names)), "duplicate precheck")
    require(set(names) == PRECHECK_NAMES, "missing or unexpected precheck")
    for tag in ("failure", "error", "skipped"):
        require(not root.findall(".//" + tag), "precheck contains " + tag)
    for suite in root.iter("testsuite"):
        for key in ("failures", "errors", "skipped"):
            require(int(suite.get(key, "0")) == 0, "precheck summary has " + key)
    return {"status": "PASS", "test_count": len(cases), "tests": sorted(names), "junit_sha256": sha(raw)}


def inspect_area(raw, metrics):
    text = raw.decode("utf-8")
    mapped = {
        "cells": int(re.search(r"^\s*(\d+)\s+\S+\s+cells$", text, re.M)[1]),
        "area_um2": float(re.search(r"Chip area for module.*:\s*(\d+\.\d+)", text)[1]),
        "sequential_area_um2": float(re.search(r"of which used for sequential elements:\s*(\d+\.\d+)", text)[1]),
        "sequential_cells": int(re.search(r"^\s*(\d+)\s+\S+\s+sg13cmos5l_dfrbpq_1$", text, re.M)[1]),
    }
    routed = {name: metrics[name] for name in ("design__instance__count__stdcell",
              "design__instance__area__stdcell", "design__instance__utilization")}
    require(all(isinstance(v, (int, float)) and math.isfinite(v) and v > 0 for v in (*mapped.values(), *routed.values())),
            "missing or invalid mapped/routed area")
    return {"mapped": mapped, "routed": routed}


def require_finished(run, jobs):
    require(run["status"] == "completed" and run["conclusion"] == "success", "physical workflow is not successfully complete")
    selected = [j for j in jobs if j["name"] in ("gds", "precheck", "gl_test")]
    require(sorted(j["name"] for j in selected) == ["gds", "gl_test", "precheck"], "missing or duplicate physical job")
    for job in selected:
        require(job["run_id"] == run["id"], "job belongs to another run")
        require(job["run_attempt"] == run["run_attempt"], "job belongs to another attempt")
        require(job["status"] == "completed" and job["conclusion"] == "success", "required physical job failed or unfinished: " + job["name"])
    return {j["name"]: j for j in selected}


def audit(directory, output, variant="od128"):
    run = read(directory / "run.json")
    jobs = require_finished(run, read(directory / "jobs.json")["jobs"])
    source = run["head_sha"]
    metadata = read(directory / "artifacts.json")["artifacts"]
    selected = [a for a in metadata if a["name"] in REQUIRED_ARCHIVES]
    require(len(selected) == len(REQUIRED_ARCHIVES) and {a["name"] for a in selected} == REQUIRED_ARCHIVES,
            "missing or duplicate required archive")
    archives = {a["name"]: Archive(directory, a, run) for a in selected}
    try:
        lock = common.candidate_lock()
        logs, submission = archives["GDS_logs"], archives["tt_submission"]
        require(variant in ("od128", "od128-lanes", "od128-shared"), "unsupported physical qualification candidate")
        inputs = archives["g2-physical-candidate"].json(variant + "/inputs.json")
        expected = physical_g2.candidate_manifest(variant)["source_sha256"]
        require(inputs["variant"] == variant and inputs["program_words"] == 128, "wrong physical candidate")
        require(inputs["workflow_source_commit"] == source and inputs["source_sha256"] == expected, "staged source identity mismatch")
        require(inputs["flow_lock"] == lock, "staged flow lock mismatch")
        require(inputs["public_test_names"] == sorted(physical_g2.PUBLIC_TEST_MODULES), "staged public selection mismatch")
        require(inputs["staged_in_ci"], "candidate was not staged in CI")
        for name, digest in inputs["provenance_sha256_lf"].items():
            require(sha(frozen(source, name)) == digest, "workflow input digest mismatch: " + name)
        if variant in ("od128-lanes", "od128-shared"):
            evidence, status = {
                "od128-lanes": ("evidence/E0037-explicit-store-lanes/qualification.json", "PASS_LANES_CANDIDATE_RTL_FORMAL"),
                "od128-shared": ("evidence/E0038-shared-program-read/qualification.json", "PASS_SHARED_CANDIDATE_RTL_FORMAL"),
            }[variant]
            qualification = frozen(source, evidence)
            require(inputs["implementation_qualification_sha256"] == sha(qualification), "implementation qualification identity mismatch")
            qualified = json.loads(qualification)
            require(qualified["status"] == status and
                    qualified["source_sha256"] == expected, "implementation source qualification mismatch")
        require(sha(frozen(source, "info.yaml")) == inputs["metadata_sha256_lf"], "metadata identity mismatch")
        config_source = inputs.get("config_source_path", "src/config.json")
        require(config_source in ("src/config.json", common.BASE_CONFIG_PATH), "unexpected physical configuration source")
        require(sha(frozen(source, config_source)) == inputs["config_sha256_lf"] == lock["config_sha256_lf"], "physical configuration mismatch")
        for archive in (logs, submission):
            for name, digest in expected.items():
                require(sha(archive.bytes("src/" + name)) == digest, "actual hardened source mismatch: " + name)
            require(sha(archive.bytes("src/config.json")) == lock["config_sha256_lf"], "hardened configuration mismatch")
        pdk = submission.json("tt_submission/pdk.json")
        require(pdk == logs.json("runs/wokwi/pdk.json"), "submission and flow PDK differ")
        require(pdk["FLOW_VERSION"] == lock["librelane"] and pdk["PDK"] == lock["pdk"]
                and pdk["PDK_VERSION"] == lock["pdk_commit"] and pdk["PDK_SOURCE"] == lock["pdk_source"], "resolved PDK/flow identity mismatch")
        resolved = submission.json("tt_submission/resolved.json")
        require(resolved == logs.json("runs/wokwi/resolved.json"), "submission and flow configuration differ")
        common.verify_run_configuration(resolved, lock)
        metrics = logs.json("runs/wokwi/final/metrics.json")
        review = common.inspect_physical_metrics(metrics)
        require(review["status"] == "PASS", "routed metrics failed: " + "; ".join(review["errors"]))
        area = inspect_area(submission.bytes("tt_submission/stats/synthesis-stats.txt"), metrics)
        layout = submission.bytes("tt_submission/" + TOP + ".gds")
        require(layout == logs.bytes("runs/wokwi/final/gds/" + TOP + ".gds"), "submitted/routed layout mismatch")
        netlist = submission.bytes("tt_submission/" + TOP + ".v")
        require(netlist == logs.bytes("runs/wokwi/final/nl/" + TOP + ".nl.v"), "submitted/routed netlist mismatch")
        require(b"sg13cmos5l_" in netlist, "submission is not a CMOS5L netlist")
        runtime = inspect_runtime((directory / "gds-job.log").read_bytes(), source, lock, jobs["gds"]["id"])
        consumers = {kind: inspect_consumed_artifact((directory / (kind + "-job.log")).read_bytes(),
                     submission.metadata, lock, jobs[kind]["id"], kind) for kind in ("precheck", "gl_test")}
        precheck = inspect_precheck(archives["precheck_reports"].bytes("results.xml"))
        check = archives["g2-netlist-check"].json("test/output/physical-result.json")
        require(check["status"] == "PASS" and check["evidence_kind"] == "FUNCTIONAL_ZERO_DELAY_NETLIST"
                and check["netlist_sha256"] == sha(netlist), "CI did not bind the tested netlist to the submission")
        test_inputs = archives["g2-netlist-check"].json("build/g2-physical/" + variant + "/inputs.json")
        require({k:v for k,v in test_inputs.items() if k != "created_utc"} ==
                {k:v for k,v in inputs.items() if k != "created_utc"}, "netlist-test source/selection differs from GDS stage")
        test = archives["gatelevel_test_results"]
        junit = output / "public-results.xml"
        junit.write_bytes(test.bytes("results.xml"))
        for name in ("spi/cases.jsonl", "i2c/cases.jsonl", "i2c/boundaries.jsonl", "i2c/aborts.jsonl"):
            path = output / "records" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(test.bytes("output/" + name))
        public = output / "public-record-audit.json"
        physical_g2.check_tests(SimpleNamespace(junit=junit, records=output / "records", output=public, require_netlist=False))
        checked = read(public)
        require({k:v for k,v in checked.items() if k not in ("evidence_kind", "netlist_sha256")} ==
                {k:v for k,v in check.items() if k not in ("evidence_kind", "netlist_sha256")}, "offline public audit and CI checker differ")
        routed = archives["g2-physical-candidate"].json(variant + "/resolved-inputs.json")
        require(routed["status"] == "PASS_PHYSICAL_METRICS_PRECHECK_AND_NETLIST_PENDING", "CI routed checker did not pass")
        require(routed["netlist_sha256"] == sha(netlist) and routed["source_sha256"] == expected
                and routed["physical_metrics"] == review, "routed checker differs from original outputs")
        require(routed["metrics_sha256"] == sha(logs.bytes("runs/wokwi/final/metrics.json"))
                and routed["resolved_config_sha256"] == sha(logs.bytes("runs/wokwi/resolved.json"))
                and routed["pdk"] == pdk, "routed output digests or PDK differ")
        return {"schema": "protocol-emulator-g2-physical-audit-v1", "status": "PASS_ALL_G2_PHYSICAL_GATES",
                "run_id": run["id"], "workflow_source_commit": source, "variant": variant,
                "source_sha256": expected, "gds_sha256": sha(layout), "netlist_sha256": sha(netlist),
                "gds_bytes": len(layout), "program_words": 128, "program_bits": 4096,
                "pdk": pdk, "physical_metrics": review, "area": area, "runtime": runtime, "consumer_artifacts": consumers,
                "precheck": precheck, "netlist_tests": check,
                "archives": {name: {"id": a.metadata["id"], "sha256": a.digest} for name,a in archives.items()},
                "scope": "Pinned digital physical qualification and functional zero-delay netlist tests; production adoption/publication are separate"}
    finally:
        for archive in archives.values():
            archive.file.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("od128", "od128-lanes", "od128-shared"), default="od128")
    args = parser.parse_args()
    out = args.output.resolve()
    require(out.is_relative_to((ROOT / "build").resolve()) and not out.exists(), "use a new output directory under build/")
    out.mkdir(parents=True)
    try:
        report = audit(args.artifacts.resolve(), out, args.variant)
    except (AssertionError, ValueError, KeyError, FileNotFoundError, ET.ParseError, zipfile.BadZipFile) as error:
        common.write_json(out / "result.json", {"status": "NOT_QUALIFIED", "error": str(error)})
        raise
    common.write_json(out / "result.json", report)
    print(report["status"])


if __name__ == "__main__":
    main()
