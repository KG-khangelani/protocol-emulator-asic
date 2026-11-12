# SPDX-License-Identifier: Apache-2.0
"""Exercise final-audit gates with retained observations and corrupted controls."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from tools import audit_g2_physical as audit
from tools import physical_runtime as runtime


class FinalPhysicalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (audit.ROOT / "build").mkdir(exist_ok=True)
        cls.historical = audit.ROOT / "evidence/E0031-8x4-physical-comparison/attempts/d34/compact10"
        cls.record = json.loads((cls.historical / "result.json").read_bytes())
        cls.lock = audit.common.candidate_lock()
        cls.logs = {name: gzip.decompress((cls.historical / (name + "-job.log.gz")).read_bytes())
                    for name in ("gds", "precheck", "gl_test")}
        cls.artifact = next(a for a in cls.record["verified_artifacts"] if a["name"] == "tt_submission")

    def test_real_g1_runtime_and_consumer_records_replay(self):
        r = self.record
        observed = runtime.inspect_runtime(self.logs["gds"], r["workflow_source_commit"], self.lock, r["jobs"]["gds"]["id"])
        retained = {k: v for k, v in r["runtime_identities"].items() if k != "retained_log"}
        retained["log_sha256"] = r["runtime_identities"]["retained_log"]["retained_decoded_log_sha256"]
        self.assertEqual(observed, retained)
        for kind, original in (("precheck", r["precheck"]), ("gl_test", r["netlist_tests"])):
            observed = runtime.inspect_consumed_artifact(self.logs[kind], self.artifact, self.lock, r["jobs"][kind]["id"], kind)
            retained = {k:v for k,v in original["input_artifact_audit"].items() if k != "retained_log"}
            retained["log_sha256"] = original["input_artifact_audit"]["retained_log"]["retained_decoded_log_sha256"]
            self.assertEqual(observed, retained)

    def test_declared_image_without_actual_pull_is_rejected(self):
        altered = re.sub(rb"^\S+Z Digest: sha256:[0-9a-f]+\s*$", b"", self.logs["gds"], flags=re.M)
        self.assertNotEqual(altered, self.logs["gds"])
        with self.assertRaisesRegex(AssertionError, "image pull digest"):
            runtime.inspect_runtime(altered, self.record["workflow_source_commit"], self.lock, 1)

    def test_wrong_source_and_submission_id_are_rejected(self):
        with self.assertRaisesRegex(AssertionError, "source checkout"):
            runtime.inspect_runtime(self.logs["gds"], "0" * 40, self.lock, 1)
        changed = dict(self.artifact, id=self.artifact["id"] + 1)
        with self.assertRaisesRegex(AssertionError, "expected submission"):
            runtime.inspect_consumed_artifact(self.logs["gl_test"], changed, self.lock, 1, "gl_test")

    def test_wrong_consumer_pdk_is_rejected(self):
        changed = self.logs["precheck"].replace(self.lock["pdk_commit"].encode(), b"0" * 40)
        with self.assertRaisesRegex(AssertionError, "PDK activation"):
            runtime.inspect_consumed_artifact(changed, self.artifact, self.lock, 1, "precheck")

    def test_precheck_requires_all_ten_unique_successes(self):
        raw = (self.historical / "precheck/results.xml").read_bytes()
        self.assertEqual(audit.inspect_precheck(raw)["test_count"], 10)
        for mode in ("missing", "duplicate", "skipped", "failed", "summary_error"):
            with self.subTest(mode=mode):
                root = ET.fromstring(raw)
                suite = root.find("testsuite")
                if mode == "missing": suite.remove(suite[0])
                elif mode == "duplicate": suite.append(copy.deepcopy(suite[0]))
                elif mode == "summary_error": suite.set("errors", "1")
                else: ET.SubElement(suite[0], "skipped" if mode == "skipped" else "failure")
                with self.assertRaises(ValueError):
                    audit.inspect_precheck(ET.tostring(root))

    def test_real_mapped_and_routed_area_replay(self):
        raw = gzip.decompress((self.historical / "synthesis-stats.txt.gz").read_bytes())
        metrics = json.loads(gzip.decompress((self.historical / "metrics.json.gz").read_bytes()))
        observed = audit.inspect_area(raw, metrics)
        self.assertEqual(observed["mapped"], self.record["mapped"])
        for key in observed["routed"]:
            self.assertEqual(observed["routed"][key], self.record["final_metrics"][key])
        metrics["design__instance__area__stdcell"] = float("nan")
        with self.assertRaisesRegex(ValueError, "invalid mapped/routed area"):
            audit.inspect_area(raw, metrics)

    def test_unfinished_failed_missing_and_mixed_jobs_are_rejected(self):
        run = {"id": 7, "status": "completed", "conclusion": "success", "run_attempt": 2}
        jobs = [dict(run_id=7, run_attempt=2, name=n, status="completed", conclusion="success")
                for n in ("gds", "precheck", "gl_test")]
        self.assertEqual(set(audit.require_finished(run, jobs)), {"gds", "precheck", "gl_test"})
        for mode in ("live", "failed", "skipped", "missing", "duplicate", "other_run", "other_attempt"):
            with self.subTest(mode=mode):
                r, j = copy.deepcopy(run), copy.deepcopy(jobs)
                if mode == "live": r["status"] = "in_progress"
                elif mode == "failed": j[0]["conclusion"] = "failure"
                elif mode == "skipped": j[1]["conclusion"] = "skipped"
                elif mode == "missing": j.pop()
                elif mode == "duplicate": j.append(j[0])
                elif mode == "other_run": j[0]["run_id"] = 8
                else: j[0]["run_attempt"] = 1
                with self.assertRaises(ValueError): audit.require_finished(r, j)

    def test_archive_requires_exact_run_source_size_and_bytes(self):
        with tempfile.TemporaryDirectory(dir=audit.ROOT / "build") as directory:
            path = Path(directory) / "9.zip"
            with zipfile.ZipFile(path, "w") as archive: archive.writestr("result.json", "{}")
            run = {"id": 7, "head_sha": "a" * 40}
            metadata = {"id": 9, "workflow_run": {"id": 7, "head_sha": "a" * 40},
                        "size_in_bytes": path.stat().st_size, "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()}
            accepted = audit.Archive(Path(directory), metadata, run)
            accepted.file.close()
            for mode in ("run", "source", "size", "digest"):
                with self.subTest(mode=mode):
                    changed = copy.deepcopy(metadata)
                    if mode == "run": changed["workflow_run"]["id"] = 8
                    elif mode == "source": changed["workflow_run"]["head_sha"] = "b" * 40
                    elif mode == "size": changed["size_in_bytes"] += 1
                    else: changed["digest"] = "sha256:" + "0" * 64
                    with self.assertRaises(ValueError): audit.Archive(Path(directory), changed, run)


if __name__ == "__main__":
    unittest.main()
