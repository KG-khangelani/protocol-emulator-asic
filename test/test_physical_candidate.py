# SPDX-License-Identifier: Apache-2.0
"""Negative controls for physical evidence acceptance and CI-only staging."""
import contextlib
import gzip
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from tools import physical_candidate as physical


class PhysicalEvidenceTests(unittest.TestCase):
    def setUp(self):
        (physical.ROOT / "build").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=physical.ROOT / "build")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def fixture(self, variant="P"):
        suite = ET.Element("testsuite")
        for name in sorted(physical.PUBLIC_TESTS):
            ET.SubElement(suite, "testcase", name=name, classname=physical.PUBLIC_TEST_MODULES[name])
        for module, name in sorted(physical.EXCLUDED_TESTS):
            case = ET.SubElement(suite, "testcase", name=name, classname=module)
            ET.SubElement(case, "skipped")
        junit = self.out / "results.xml"
        ET.ElementTree(suite).write(junit)
        source = physical.E0030 / variant / "public-icarus/records/cases.jsonl.gz"
        rows = [json.loads(line) for line in gzip.decompress(source.read_bytes()).decode().splitlines()]
        rows = [row for row in rows if "trace_sha256" in row]
        records = self.out / "cases.jsonl"
        records.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return SimpleNamespace(variant=variant, junit=junit, records=records,
                               output=self.out / "check.json", require_netlist=False)

    def test_retained_public_records_are_accepted_for_each_variant(self):
        for variant in ("P", "compact10"):
            with contextlib.redirect_stdout(io.StringIO()):
                physical.check_tests(self.fixture(variant))
            record = physical.read_json(self.out / "check.json")
            self.assertEqual(record["evidence_kind"], "RTL_WITHOUT_DIRECT_ENGINE")
            self.assertIsNone(record["netlist_sha256"])

    def test_missing_transfer_is_rejected(self):
        args = self.fixture()
        rows = args.records.read_text(encoding="utf-8").splitlines()
        args.records.write_text("\n".join(rows[:-1]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing or extra SPI"):
            physical.check_tests(args)

    def test_skipped_test_is_rejected(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        ET.SubElement(tree.getroot()[0], "skipped")
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "failed or skipped"):
            physical.check_tests(args)

    def test_forged_trace_hash_is_rejected(self):
        args = self.fixture()
        rows = args.records.read_text(encoding="utf-8").splitlines()
        first = json.loads(rows[0])
        first["trace_sha256"] = "0" * 64
        rows[0] = json.dumps(first)
        args.records.write_text("\n".join(rows) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "records differ"):
            physical.check_tests(args)

    def test_missing_required_group_is_rejected(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        tree.getroot().remove(tree.getroot()[0])
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "missing required"):
            physical.check_tests(args)

    def test_unknown_skipped_group_is_rejected(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        case = ET.SubElement(tree.getroot(), "testcase", name="unknown", classname="test")
        ET.SubElement(case, "skipped")
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "unexpected test"):
            physical.check_tests(args)

    def test_excluded_group_cannot_run_silently(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        case = tree.getroot()[-1]
        case.remove(case.find("skipped"))
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "unexpected test"):
            physical.check_tests(args)



    def resolved_fixture(self):
        path = (physical.ROOT / "evidence/E0031-8x4-physical-comparison/attempts/"
                "template-default/P/resolved.json.gz")
        resolved = json.loads(gzip.decompress(path.read_bytes()))
        resolved.update(physical.candidate_lock()["physical_constraints"])
        return resolved

    def test_revised_shared_settings_are_required(self):
        lock = physical.candidate_lock()
        physical.verify_run_configuration(self.resolved_fixture(), lock)
        for name, old_value in (("MAX_FANOUT_CONSTRAINT", 10),
                                ("CTS_SINK_CLUSTERING_SIZE", None),
                                ("CTS_DISTANCE_BETWEEN_BUFFERS", 0)):
            with self.subTest(setting=name):
                resolved = self.resolved_fixture()
                resolved[name] = old_value
                with self.assertRaisesRegex(ValueError, name):
                    physical.verify_run_configuration(resolved, lock)

    def test_missing_signoff_corner_is_rejected(self):
        resolved = self.resolved_fixture()
        resolved["STA_CORNERS"] = resolved["STA_CORNERS"][:-1]
        with self.assertRaisesRegex(ValueError, "corner set"):
            physical.verify_run_configuration(resolved, physical.candidate_lock())

    def metrics_fixture(self, clear_fanout=True):
        path = (physical.ROOT / "evidence/E0031-8x4-physical-comparison/attempts/"
                "template-default/P/metrics.json.gz")
        metrics = json.loads(gzip.decompress(path.read_bytes()))
        if clear_fanout:
            # Synthetic acceptance fixture; the actual failed attempt stays immutable.
            for key in metrics:
                if key.startswith("design__max_fanout_violation__count"):
                    metrics[key] = 0
        return metrics

    def test_original_green_build_is_rejected_for_fanout(self):
        result = physical.inspect_physical_metrics(self.metrics_fixture(False))
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("fanout" in error and "30" in error for error in result["errors"]))

    def test_clean_metrics_fixture_is_accepted(self):
        self.assertEqual(physical.inspect_physical_metrics(self.metrics_fixture())["status"], "PASS")

    def test_each_corner_requires_setup_and_hold(self):
        for corner in physical.SIGNOFF_CORNERS:
            for kind in ("setup", "hold"):
                with self.subTest(corner=corner, kind=kind):
                    metrics = self.metrics_fixture()
                    metrics[f"timing__{kind}__ws__corner:{corner}"] = -0.001
                    self.assertEqual(physical.inspect_physical_metrics(metrics)["status"], "FAIL")

    def test_missing_and_nonfinite_results_cannot_pass(self):
        key = "timing__setup__ws__corner:nom_slow_1p08V_125C"
        for value in (None, float("nan"), float("inf"), "0", True):
            with self.subTest(value=value):
                metrics = self.metrics_fixture()
                metrics[key] = value
                result = physical.inspect_physical_metrics(metrics)
                self.assertEqual(result["status"], "FAIL")
                json.dumps(result, allow_nan=False)
        metrics = self.metrics_fixture()
        del metrics[key]
        self.assertEqual(physical.inspect_physical_metrics(metrics)["status"], "FAIL")

    def test_physical_and_electrical_failures_cannot_pass(self):
        for key in ("route__drc_errors", "route__antenna_violation__count",
                    "antenna__violating__nets", "antenna__violating__pins",
                    "magic__drc_error__count", "design__lvs_error__count",
                    "design__power_grid_violation__count",
                    "design__max_fanout_violation__count__corner:nom_fast_1p32V_m40C",
                    "design__max_cap_violation__count__corner:nom_slow_1p08V_125C",
                    "design__max_slew_violation__count__corner:nom_typ_1p20V_25C"):
            with self.subTest(key=key):
                metrics = self.metrics_fixture()
                metrics[key] = 1
                self.assertEqual(physical.inspect_physical_metrics(metrics)["status"], "FAIL")

    def test_in_place_staging_refuses_non_ci_without_creating_output(self):
        out = self.out / "must-not-exist"
        with patch.dict("os.environ", {"GITHUB_ACTIONS": "false"}):
            with self.assertRaisesRegex(ValueError, "CI-only"):
                physical.prepare(SimpleNamespace(output=out, variant="P", stage_ci=True))
        self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
