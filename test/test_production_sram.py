# SPDX-License-Identifier: Apache-2.0
"""Attempt real-source and rehashed semantic faults against the adopted profile."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.production_sram import verify

ROOT = Path(__file__).resolve().parents[1]
read = lambda path: json.loads(path.read_bytes())
sha = lambda raw: hashlib.sha256(raw).hexdigest()


@unittest.skipUnless((ROOT / 'tools/production-profile.json').is_file(), 'no production adoption in this historical revision')
class ProductionIdentityTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='production-controls-', dir=ROOT / 'build')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = read(ROOT / 'tools/production-profile.json')
        names = set(self.profile['files_sha256']) | {'tools/production-profile.json', 'info.yaml', self.profile['decision']}
        names.update(self.profile[key]['path'] for key in
                     ('qualification', 'combined_regression', 'normal_command_verification', 'corrected_netlist_pair'))
        for name in names:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        # Every fault starts from the actual adopted files and a passing guard.
        self.baseline = verify(self.root)

    def write(self, name, value):
        (self.root / name).write_bytes((json.dumps(value, indent=2) + '\n').encode())

    def reseal(self, reference, transform):
        name = self.profile[reference]['path']
        value = read(self.root / name)
        transform(value)
        self.write(name, value)
        self.profile[reference]['sha256'] = sha((self.root / name).read_bytes())
        self.write('tools/production-profile.json', self.profile)

    def test_actual_production_matches_the_qualified_netlist_and_sources(self):
        self.assertEqual(self.baseline['status'], 'PASS_PRODUCTION_MATCHES_QUALIFIED_SRAM')
        self.assertEqual(self.baseline['qualified_netlist_sha256'], self.profile['qualification']['netlist_sha256'])
        self.assertEqual(len(self.baseline['files_sha256']), 20)

    def test_changed_rtl_cannot_borrow_qualification(self):
        path = self.root / 'src/m1_engine.v'
        path.write_bytes(path.read_bytes() + b'\n// deliberately changed candidate\n')
        with self.assertRaisesRegex(ValueError, 'production input differs: src/m1_engine.v'):
            verify(self.root)

    def test_changed_flow_or_power_helper_cannot_borrow_qualification(self):
        for name in ('src/config.json', 'select_sram_power_ports.py'):
            with self.subTest(name=name):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                with self.assertRaisesRegex(ValueError, 'production input differs'):
                    verify(self.root)
                path.write_bytes(original)

    def test_rehashed_failed_physical_job_is_rejected(self):
        self.reseal('qualification', lambda value: value['jobs']['precheck'].update(conclusion='failure'))
        with self.assertRaisesRegex(ValueError, 'incomplete physical gates'):
            verify(self.root)

    def test_rehashed_wrong_netlist_pair_is_rejected(self):
        self.reseal('corrected_netlist_pair', lambda value: value.update(netlist_sha256='0' * 64))
        with self.assertRaisesRegex(ValueError, 'qualified netlist differs from both-simulator pair'):
            verify(self.root)

    def test_rehashed_incomplete_precheck_is_rejected(self):
        self.reseal('qualification', lambda value: value['precheck'].update(test_count=9))
        with self.assertRaisesRegex(ValueError, 'complete official precheck missing'):
            verify(self.root)

    def test_rehashed_changed_clock_is_rejected(self):
        path = self.root / 'info.yaml'
        original = path.read_bytes()
        self.assertIn(b'50000000', original)
        path.write_bytes(original.replace(b'50000000', b'40000000'))
        self.profile['metadata_sha256'] = sha(path.read_bytes())
        self.write('tools/production-profile.json', self.profile)
        with self.assertRaisesRegex(ValueError, 'production footprint or clock changed'):
            verify(self.root)

    def test_missing_combined_regression_is_rejected(self):
        (self.root / self.profile['combined_regression']['path']).unlink()
        with self.assertRaisesRegex(ValueError, 'missing production input'):
            verify(self.root)

    def test_changed_decision_is_rejected(self):
        path = self.root / self.profile['decision']
        path.write_bytes(path.read_bytes() + b'\nchanged adoption boundary\n')
        with self.assertRaisesRegex(ValueError, 'production decision changed'):
            verify(self.root)


if __name__ == '__main__':
    unittest.main()
