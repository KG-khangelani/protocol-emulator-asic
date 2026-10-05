"""Falsification checks for retained waveform labels and checksums."""

import tempfile
from pathlib import Path
import unittest

from tools.check_waveform_provenance import ProvenanceError, build_manifest, create_checkpoint


def write_junit(path, module, test_name, sim_time_ns):
    modules = module if isinstance(module, (list, tuple)) else [module]
    path.write_text(
        '<testsuites><testsuite name="all">' + "".join(
            f'<testcase classname="{name}" name="{test_name}" sim_time_ns="{sim_time_ns}" />'
            for name in modules) +
        "</testsuite></testsuites>"
    )


class WaveformProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.rtl_waveform = root / "rtl.fst"
        self.rtl_junit = root / "rtl.xml"
        self.gl_waveform = root / "gl.fst"
        self.gl_junit = root / "gl.xml"
        self.rtl_waveform.write_bytes(b"full-rtl-waveform")
        self.gl_waveform.write_bytes(b"short-gl-smoke-waveform")
        write_junit(self.rtl_junit, ["test", "test_uart_rx_public"], "full_regression", 100.0)
        write_junit(
            self.gl_junit,
            "test_gate_harness_smoke",
            "public_handles_reset_without_direct_engine",
            11.0,
        )

    def tearDown(self):
        self.temp.cleanup()

    def build(self, checkpoint):
        return build_manifest(
            checkpoint,
            self.rtl_waveform,
            self.rtl_junit,
            self.gl_waveform,
            self.gl_junit,
        )

    def test_distinct_labels_retain_both_checksums(self):
        checkpoint = create_checkpoint(self.rtl_waveform, self.rtl_junit)
        manifest = self.build(checkpoint)
        simulations = manifest["simulations"]
        self.assertEqual(set(simulations), {"rtl_icarus", "gl_harness_smoke"})
        self.assertNotEqual(
            simulations["rtl_icarus"]["waveform"]["sha256"],
            simulations["gl_harness_smoke"]["waveform"]["sha256"],
        )

    def test_later_overwrite_of_rtl_waveform_is_rejected(self):
        checkpoint = create_checkpoint(self.rtl_waveform, self.rtl_junit)
        self.rtl_waveform.write_bytes(b"overwritten-by-smoke")
        with self.assertRaisesRegex(ProvenanceError, "changed after their checkpoint"):
            self.build(checkpoint)

    def test_incomplete_or_unknown_full_modules_are_rejected(self):
        for modules in (["test"], ["test_uart_rx_public"],
                        ["test", "test_uart_rx_public", "unknown"]):
            with self.subTest(modules=modules):
                write_junit(self.rtl_junit, modules, "filtered_regression", 100.0)
                checkpoint = create_checkpoint(self.rtl_waveform, self.rtl_junit)
                with self.assertRaisesRegex(ProvenanceError, "full test modules"):
                    self.build(checkpoint)

    def test_swapped_junit_label_is_rejected(self):
        checkpoint = create_checkpoint(self.rtl_waveform, self.rtl_junit)
        write_junit(
            self.rtl_junit,
            "test_gate_harness_smoke",
            "public_handles_reset_without_direct_engine",
            100.0,
        )
        checkpoint = create_checkpoint(self.rtl_waveform, self.rtl_junit)
        with self.assertRaisesRegex(ProvenanceError, "full test module"):
            self.build(checkpoint)


if __name__ == "__main__":
    unittest.main()
