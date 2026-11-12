# SPDX-License-Identifier: Apache-2.0
"""Reject missing G2 coverage, changed traces and falsely labelled netlists."""
import contextlib
import gzip
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from tools import physical_g2 as physical


class G2PhysicalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=physical.ROOT / "build")
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def fixture(self):
        suite = ET.Element("testsuite")
        for name, module in physical.PUBLIC_TEST_MODULES.items():
            ET.SubElement(suite, "testcase", name=name, classname=module)
        for module, name in physical.common.EXCLUDED_TESTS:
            case = ET.SubElement(suite, "testcase", name=name, classname=module)
            ET.SubElement(case, "skipped")
        junit = self.out / "results.xml"
        ET.ElementTree(suite).write(junit)
        paths = {
            "spi/cases.jsonl": "architecture/combined/icarus/records/cases.jsonl.gz",
            "i2c/cases.jsonl": "od128/protocols/icarus/records/cases.jsonl.gz",
            "i2c/boundaries.jsonl": "architecture/boundaries/od128-icarus/records/boundaries.jsonl.gz",
            "i2c/aborts.jsonl": "architecture/aborts/od128-icarus/records/aborts.jsonl.gz",
        }
        for target, source in paths.items():
            path = self.out / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.decompress((physical.EVIDENCE / "ci" / source).read_bytes()))
        return SimpleNamespace(junit=junit, records=self.out, output=self.out / "check.json", require_netlist=False)

    def check(self, args):
        with contextlib.redirect_stdout(io.StringIO()):
            physical.check_tests(args)

    def test_complete_fixture_is_rtl_only(self):
        args = self.fixture()
        self.check(args)
        result = physical.read_json(args.output)
        self.assertEqual(result["public_test_groups"], 18)
        self.assertEqual(result["evidence_kind"], "RTL_WITHOUT_DIRECT_ENGINE")
        self.assertIsNone(result["netlist_sha256"])

    def test_missing_required_group_fails(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        tree.getroot().remove(tree.getroot()[12])
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "missing required"):
            self.check(args)

    def test_skipped_i2c_group_fails(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        for case in tree.getroot():
            if case.get("name") == "complete_i2c_transactions":
                ET.SubElement(case, "skipped")
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "required public test skipped"):
            self.check(args)

    def test_every_record_set_requires_full_count_and_unchanged_traces(self):
        for name in ("spi/cases.jsonl", "i2c/cases.jsonl", "i2c/boundaries.jsonl", "i2c/aborts.jsonl"):
            for mutation in ("missing", "changed"):
                with self.subTest(records=name, mutation=mutation):
                    args = self.fixture()
                    path = self.out / name
                    original = path.read_text()
                    if mutation == "missing":
                        path.write_text("\n".join(original.splitlines()[:-1]) + "\n")
                    else:
                        lines = original.splitlines()
                        first = json.loads(lines[0])
                        key = "trace_sha256" if "trace_sha256" in first else "sha256"
                        first[key] = "0" * 64
                        lines[0] = json.dumps(first)
                        path.write_text("\n".join(lines) + "\n")
                        self.assertTrue(path.read_text() != original)
                    with self.assertRaisesRegex(ValueError, "missing or extra|records differ"):
                        self.check(args)

    def test_duplicate_group_fails(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        tree.getroot().append(ET.fromstring(ET.tostring(tree.getroot()[0])))
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.check(args)

    def test_unknown_exclusion_fails(self):
        args = self.fixture()
        tree = ET.parse(args.junit)
        case = ET.SubElement(tree.getroot(), "testcase", classname="test", name="unknown")
        ET.SubElement(case, "skipped")
        tree.write(args.junit)
        with self.assertRaisesRegex(ValueError, "unexpected test"):
            self.check(args)

    def test_rtl_cannot_be_labelled_as_cmos5l_netlist(self):
        args = self.fixture()
        args.require_netlist = True
        for directory, filename in (("test", "gate_level_netlist.v"),
                                    ("tt_submission", "tt_um_khangelani_protocol_emulator.v")):
            path = self.out / directory / filename
            path.parent.mkdir()
            path.write_text("module behavioral; endmodule\n")
        with patch.object(physical, "ROOT", self.out):
            with self.assertRaisesRegex(ValueError, "not a CMOS5L netlist"):
                self.check(args)

    def test_mismatched_netlist_bytes_fail(self):
        args = self.fixture()
        args.require_netlist = True
        for directory, filename, text in (("test", "gate_level_netlist.v", "sg13cmos5l_tested"),
                                          ("tt_submission", "tt_um_khangelani_protocol_emulator.v", "sg13cmos5l_submitted")):
            path = self.out / directory / filename
            path.parent.mkdir()
            path.write_text(text)
        with patch.object(physical, "ROOT", self.out):
            with self.assertRaisesRegex(ValueError, "netlist mismatch"):
                self.check(args)


if __name__ == "__main__":
    unittest.main()
