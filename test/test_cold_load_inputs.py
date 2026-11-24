# SPDX-License-Identifier: Apache-2.0
"""Check the product's artifact boundary before it can start a simulator."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.assembler import json_bytes
from tools.cold_load import ROOT, UART_BINARY, execute, stage_image
from tools.host_transport.controller import read_image


class ColdLoadInputs(unittest.TestCase):
    def setUp(self):
        (ROOT / 'build').mkdir(exist_ok=True)
        scratch = tempfile.TemporaryDirectory(dir=ROOT / 'build')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.image_dir = self.root / 'image'
        self.image, self.plan = stage_image(self.image_dir, None)

    def test_default_artifacts_are_usable_as_caller_input(self):
        staged, plan = stage_image(self.root / 'copied', self.image_dir)
        self.assertEqual(staged['binary_sha256'], UART_BINARY)
        self.assertEqual(plan, self.plan)
        self.assertEqual(len((self.image_dir / 'program.bin').read_bytes()), 32)

    def test_altered_binary_stops_before_simulation_and_preserves_failed_run(self):
        binary = self.image_dir / 'program.bin'
        data = bytearray(binary.read_bytes())
        data[1] ^= 1
        binary.write_bytes(data)
        output = self.root / 'failed'
        with patch('tools.cold_load.simulate') as simulator:
            with self.assertRaisesRegex(ValueError, 'program.bin differs'):
                execute(output, 'icarus', self.image_dir)
            simulator.assert_not_called()
        failure = (output / 'result.json').read_bytes()
        self.assertEqual(json.loads(failure)['status'], 'FAILED')
        with self.assertRaises(FileExistsError):
            execute(output, 'icarus', self.image_dir)
        self.assertEqual((output / 'result.json').read_bytes(), failure)

    def test_missing_readback_and_wrong_field_type_fail(self):
        path = self.image_dir / 'load-plan.json'
        for transform in ('omit-read', 'wrong-type'):
            with self.subTest(transform=transform):
                plan = json.loads(json_bytes(self.plan))
                if transform == 'omit-read':
                    del plan['steps'][next(i for i, s in enumerate(plan['steps'])
                                           if s['action'] == 'read_byte_after_edge')]
                else:
                    plan['steps'][0]['host_drives_uio'] = 0
                path.write_bytes(json_bytes(plan))
                with self.assertRaisesRegex(ValueError, 'load-plan.json differs'):
                    read_image(self.image_dir)

    def test_custom_source_identity_must_be_recordable(self):
        self.image['source_sha256'] = 'unknown'
        (self.image_dir / 'program.json').write_bytes(json_bytes(self.image))
        with self.assertRaisesRegex(ValueError, 'source digest'):
            read_image(self.image_dir)
