# SPDX-License-Identifier: Apache-2.0
"""Reject stale or incomplete verification receipts before evidence can reuse them."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from current_profile import describe
from current_run import load_receipt, retained_files, semantic_check, write


class CurrentEvidenceTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='current-controls-', dir=ROOT / 'build')
        self.addCleanup(self.temp.cleanup)
        self.artifacts = Path(self.temp.name)
        self.stage = self.artifacts / 'runs/smoke'
        self.stage.mkdir(parents=True)
        self.profile = describe(ROOT / 'evidence/E0038-shared-program-read/sources/od128')
        self.inputs = {'test/test_gate_harness_smoke.py': 'unit-fixture-input-identity'}
        (self.stage / 'results.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0"><testcase classname="test_gate_harness_smoke" name="public_handles_reset_without_direct_engine" /></testsuite></testsuites>')
        # A small fixture tests receipt integrity, not the waveform or chip behavior.
        (self.stage / 'tb-gl-harness.fst').write_bytes(b'unit-fixture-waveform')
        self.receipt = {'schema': 'protocol-emulator-current-stage-v1', 'status': 'PASS', 'action': 'smoke',
                        'profile': self.profile, 'verification_inputs': self.inputs, 'runtime_identity': 'pinned-runtime',
                        'commands': [{'returncode': 0}], 'directory': self.stage.relative_to(ROOT).as_posix(),
                        'artifact_sha256': retained_files(self.stage),
                        'summary': semantic_check('smoke', self.stage, self.profile)}
        self.path = self.artifacts / 'receipts/smoke.json'
        write(self.path, self.receipt)

    def load(self, **kwargs):
        return load_receipt(self.artifacts, 'smoke', kwargs.get('profile', self.profile),
                            kwargs.get('inputs', self.inputs), kwargs.get('runtime', 'pinned-runtime'))

    def test_complete_receipt_and_declared_profiles(self):
        self.assertEqual(self.load(), self.receipt)
        self.assertEqual(self.profile['program_words'], 128)
        self.assertEqual(describe(ROOT / 'experiments/spi_phase/baseline')['profile'], 'legacy8')

    def test_changed_code_source_or_runtime_cannot_reuse(self):
        changed = copy.deepcopy(self.profile)
        changed['source_sha256']['project.v'] = 'different'
        for kwargs in ({'inputs': {'test/test_gate_harness_smoke.py': 'changed'}}, {'profile': changed}, {'runtime': 'different'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AssertionError):
                self.load(**kwargs)

    def test_missing_changed_or_extra_artifacts_cannot_reuse(self):
        path = self.stage / 'tb-gl-harness.fst'
        original = path.read_bytes()
        path.unlink()
        with self.assertRaises(AssertionError):
            self.load()
        path.write_bytes(original + b'changed')
        with self.assertRaises(AssertionError):
            self.load()
        path.write_bytes(original)
        (self.stage / 'unexpected.json').write_text('{}')
        with self.assertRaises(AssertionError):
            self.load()

    def test_rehashed_skipped_test_still_rejected(self):
        xml = self.stage / 'results.xml'
        xml.write_text(xml.read_text().replace(' />', '><skipped /></testcase>'))
        self.receipt['artifact_sha256'] = retained_files(self.stage)
        write(self.path, self.receipt)
        with self.assertRaises(AssertionError):
            self.load()

    def test_failed_or_running_stage_cannot_reuse(self):
        for state in ('RUNNING', 'FAILED_OR_INCOMPLETE'):
            with self.subTest(state=state), self.assertRaises(AssertionError):
                write(self.path, dict(self.receipt, status=state))
                self.load()

    def test_repository_metadata_checks_are_never_reused(self):
        receipt = dict(self.receipt, action='check', summary={'kind': 'REPOSITORY_CHECKS'})
        write(self.artifacts / 'receipts/check.json', receipt)
        with self.assertRaisesRegex(AssertionError, 'repository checks must run fresh'):
            load_receipt(self.artifacts, 'check', self.profile, self.inputs, 'pinned-runtime')

    def test_unknown_source_cannot_fall_back_to_legacy(self):
        sources = self.artifacts / 'unknown'
        sources.mkdir()
        frozen = ROOT / 'evidence/E0038-shared-program-read/sources/od128'
        for name in self.profile['source_sha256']:
            (sources / name).write_bytes((frozen / name).read_bytes())
        with (sources / 'project.v').open('ab') as stream:
            stream.write(b'\n// unqualified change\n')
        with self.assertRaises(ValueError):
            describe(sources)


if __name__ == '__main__':
    unittest.main()
