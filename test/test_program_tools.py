# SPDX-License-Identifier: Apache-2.0
"""Assembler acceptance against reviewed words, protocol schedules and real CLI use."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.assembler import AssemblyError, artifacts, assemble, load_plan, program_bytes
from tools.program_examples import EXAMPLES, build
from experiments.i2c.general_programs import image as i2c_image, encode as i2c_encode
from experiments.spi_phase.four_mode_programs import image as spi_image
from experiments.spi_phase.phase_programs import encode as phase_encode
from tools.spi_four_mode_oracle import timing
from tools.uart_rx_oracle import rx_program

HEADER = '.target od128-sram-v1\n'


class ProgramToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / 'build').mkdir(exist_ok=True)
        cls.catalog = json.loads((EXAMPLES / 'examples.json').read_bytes())['examples']

    def example(self, name):
        return assemble((EXAMPLES / (name + '.asm')).read_text(encoding='utf-8'))

    def test_reviewed_encoding_vectors(self):
        vectors = [
            ('SET mask=0xa5 value=0x96 oe=0x3c', '00a53c96'),
            ('WAIT cycles=65535', '4000ffff'),
            ('WAIT_PIN pin=7 level=1 timeout=65535', 'fc00ffff'),
            ('SHIFT_STEP tx=0 rx=1 order=msb drive=open_drain payload=TX1', 'b0400003'),
            ('SHIFT_BURST tx=0 rx=1 order=lsb period=434', 'a0603640'),
            ('DRIVE tx=0 rx=1 order=msb mask=12 value=4', 'b0486020'),
            ('SAMPLE tx=0 rx=1 order=msb delay=23', 'b05000b8'),
        ]
        for source, expected in vectors:
            with self.subTest(source=source):
                self.assertEqual(assemble(HEADER + source + '\nHALT\n')['words'], [expected, '80000000'])
        source = HEADER + 'WAIT_PIN pin=1 level=0 timeout=0 on_timeout=cleanup\nWAIT cycles=0\ncleanup: HALT\n'
        self.assertEqual(assemble(source)['words'], ['c9020000', '40000000', '80000000'])

    def test_all_examples_match_preserved_independent_encoders(self):
        self.assertEqual(len(self.catalog), 13)
        for entry in self.catalog:
            with self.subTest(name=entry['name']):
                image = self.example(entry['name'])
                self.assertEqual(image['words'], entry['expected_words'])
                self.assertEqual(image['binary_sha256'], entry['binary_sha256'])
                self.assertEqual(image['warnings'], [])
                if entry['protocol'] == 'i2c':
                    program, data, _ = i2c_image(entry['kind'], entry['address'], entry['tx'])
                    words = [i2c_encode(inst) for inst in program]
                    self.assertEqual(image['payloads'], {'TX0': data[1], 'TX1': data[4]})
                elif entry['protocol'] == 'spi':
                    program, _ = spi_image(entry['mode'], entry['order'], 'held')
                    words = [phase_encode(inst) for inst in program]
                elif entry['protocol'] == 'uart_rx':
                    words = [(0xC0000000 | inst.pin << 27 | inst.level << 26 | inst.count)
                             if inst.opcode == 'WAIT_PIN' else phase_encode(inst) for inst in rx_program(434)]
                else:
                    continue  # UART TX also has an independent fixed frame-schedule check below.
                self.assertEqual(image['words'], [f'{word:08x}' for word in words])

    def test_deterministic_artifacts_across_line_endings(self):
        source = (EXAMPLES / 'i2c_write_read.asm').read_text(encoding='utf-8')
        self.assertEqual(artifacts(assemble(source)), artifacts(assemble(source.replace('\n', '\r\n'))))

    def test_binary_is_little_endian_without_hidden_header(self):
        image = assemble(HEADER + 'SET mask=0x12 value=0x56 oe=0x34\nHALT\n')
        self.assertEqual(program_bytes(image), bytes.fromhex('56341200 00000080'))

    def test_integer_symbols_and_forward_labels(self):
        source = HEADER + '.const PERIOD 434\n.const HALF PERIOD//2\nWAIT cycles=HALF-2\nWAIT_PIN pin=0 level=1 timeout=(1<<8)-1 on_timeout=done\nSET mask=1 value=0 oe=1\ndone: HALT\n'
        image = assemble(source)
        self.assertEqual(image['words'], ['400000d7', 'c50300ff', '00010100', '80000000'])
        self.assertEqual(image['labels']['done'], 3)

    def test_capacity_boundary_never_truncates(self):
        body = 'WAIT cycles=0\n' * 127 + 'HALT\n'
        self.assertEqual(len(program_bytes(assemble(HEADER + body))), 512)
        with self.assertRaisesRegex(AssemblyError, 'exceeds 128'):
            assemble(HEADER + 'WAIT cycles=0\n' + body)

    def test_loop_span_and_zero_count(self):
        source = HEADER + 'LOOP count=255 end=done\n' + 'WAIT cycles=0\n' * 31 + 'done: HALT\n'
        image = assemble(source)
        self.assertEqual(image['words'][0], '7f0000ff')
        self.assertEqual(image['schedule']['halt_edge'], 31 * 255 + 2)
        image = assemble(HEADER + 'LOOP count=0 end=done\nHALT\ndone: HALT\n')
        self.assertEqual(image['schedule']['halt_edge'], 2)
        with self.assertRaisesRegex(AssemblyError, 'maximum is 31'):
            assemble(source.replace('done: HALT', 'WAIT cycles=0\ndone: HALT'))

    def test_nested_loop_halt_and_skip_in_active_body_are_diagnosed(self):
        for body in ('HALT', 'LOOP count=0 end=done', 'WAIT_PIN pin=0 level=0 timeout=1 on_timeout=skip'):
            with self.subTest(body=body), self.assertRaisesRegex(AssemblyError, 'nonzero LOOP body'):
                assemble(HEADER + 'LOOP count=2 end=done\n' + body + '\nWAIT cycles=0\ndone: HALT\n')

    def test_bad_operands_reserved_encodings_and_targets(self):
        bad = ['SET mask=256 value=0 oe=0', 'SET mask=1 value=0 oe=-1', 'SET mask=1 value=0',
               'SET mask=1 value=0 oe=1 delay=2', 'WAIT cycles=65536', 'WAIT cycles=0 cycles=1',
               'WAIT_PIN pin=8 level=0 timeout=0', 'WAIT_PIN pin=1 level=2 timeout=0',
               'WAIT_PIN pin=1 level=0 timeout=0 on_timeout=missing',
               'WAIT_PIN pin=1 level=0 timeout=0 on_timeout=128',
               'WAIT_PIN pin=1 level=0 timeout=0 on_timeout=skip',
               'SHIFT_STEP tx=1 rx=1 order=lsb', 'SHIFT_STEP tx=0 rx=1 order=middle',
               'SHIFT_STEP tx=0 rx=1 order=lsb payload=TX2',
               'SHIFT_BURST tx=0 rx=1 order=msb period=1',
               'SHIFT_BURST tx=0 rx=1 order=msb period=2 drive=open_drain',
               'DRIVE tx=0 rx=1 order=msb mask=3 value=0',
               'SAMPLE tx=0 rx=1 order=msb delay=65536', 'HALT extra=1', '.word 0xffffffff']
        for statement in bad:
            with self.subTest(statement=statement), self.assertRaises(AssemblyError) as context:
                assemble(HEADER + statement + '\nHALT\n')
            self.assertEqual(context.exception.line, 2)

    def test_symbol_declaration_errors(self):
        for source in ('.const x 1\nx: HALT', '.const x y\nHALT', '.data TX0 1\n.data TX0 2\nHALT',
                       '.data RX 1\nHALT', '.idle 256\nHALT', '.const fault 1\nHALT',
                       'x: WAIT cycles=0\nx: HALT'):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(HEADER + source + '\n')

    def test_expression_language_cannot_execute_python(self):
        for value in ('__import__("os").getcwd()', 'True', '[1][0]', '1/2', '2**1000000',
                      '1<<1000000', '1//0', '1<<-1', '1<<63<<1', '1+' * 70 + '1'):
            with self.subTest(value=value), self.assertRaises(AssemblyError):
                assemble(HEADER + f'WAIT cycles={value}\nHALT\n')

    def test_target_and_empty_input_fail_closed(self):
        for source in ('HALT\n', '.target legacy8\nHALT\n', HEADER, HEADER + HEADER + 'HALT\n'):
            with self.subTest(source=source), self.assertRaises(AssemblyError):
                assemble(source)

    def test_fixed_uart_schedule_matches_frame_mathematics(self):
        schedule = self.example('uart_tx')['schedule']
        self.assertEqual(schedule['status'], 'FIXED_DISPATCH')
        self.assertEqual(schedule['halt_edge'], 3 + 20 * 434)
        self.assertEqual(schedule['positions']['2'], {'first_edge': 3, 'last_edge': 4343, 'executions': 2})
        self.assertEqual(schedule['positions']['4'], {'first_edge': 437, 'last_edge': 4777, 'executions': 2})

    def test_spi_schedule_matches_independent_wire_oracle(self):
        for mode in range(4):
            for order in ('lsb', 'msb'):
                expected = timing(mode, 2 if mode & 1 else 3)
                schedule = self.example(f'spi_mode{mode}_{order}')['schedule']
                self.assertEqual(schedule['halt_edge'], expected['halt'])

    def test_external_choices_and_backward_branch_do_not_invent_a_total(self):
        for name in ('uart_rx', 'i2c_write', 'i2c_read', 'i2c_write_read'):
            schedule = self.example(name)['schedule']
            self.assertEqual(schedule['status'], 'INPUT_DEPENDENT')
            self.assertIsNone(schedule['halt_edge'])
        image = assemble(HEADER + 'again: WAIT_PIN pin=0 level=1 timeout=2 on_timeout=again\nHALT\n')
        self.assertIn('finite total runtime', image['warnings'][0])

    def test_load_plan_covers_all_banks_and_commits_after_readback(self):
        for length in (1, 8, 9, 128):
            image = assemble(HEADER + 'SET mask=1 value=0 oe=1\n' * (length - 1) + 'HALT\n')
            steps = load_plan(image)['steps']
            self.assertEqual(steps[1]['expected']['uo_out'], 0x22)
            self.assertEqual([s['uio_in'] for s in steps if s['action'] == 'write_bank'], list(range((length+7)//8)))
            self.assertEqual(sum(s['action'] == 'read_byte_after_edge' for s in steps), length * 4)
            commit = next(i for i, s in enumerate(steps) if s['action'] == 'commit_length')
            self.assertTrue(all(s['action'] != 'read_byte_after_edge' for s in steps[commit:]))
            self.assertEqual(steps[commit]['uio_in'], length)
            self.assertTrue(all(not s['host_drives_uio'] for s in steps if s['expected'].get('uio_oe') == 255))
            self.assertEqual([s['ena'] for s in steps[-2:]], [0, 0])

    def test_corrupted_program_cannot_make_a_load_plan(self):
        image = self.example('uart_tx')
        for key, value in (('target', 'legacy8'), ('interface_id', 0x21), ('binary_sha256', '0' * 64), ('words', ['ffffffff'])):
            broken = copy.deepcopy(image)
            broken[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_plan(broken)
        for override in ({'TX0': 256}, {'RX': 1}, {'TX0': True}):
            with self.assertRaises(ValueError):
                load_plan(image, payloads=override)

    def test_cli_error_does_not_create_output_and_reports_line(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            path = Path(folder)
            source = path / 'bad.asm'
            source.write_text(HEADER + 'WAIT cycles=65536\nHALT\n', encoding='utf-8')
            proc = subprocess.run([sys.executable, str(ROOT/'tools/assembler.py'), str(source), '--out', str(path/'out')],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertIn('bad.asm:2: error: cycles must be 0..65535', proc.stderr)
            self.assertFalse((path / 'out').exists())

    def test_clean_example_builds_are_reproducible(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
            path = Path(folder)
            first, second = build(path / 'first'), build(path / 'second')
            self.assertEqual(first, second)
            for file in (path/'first').rglob('*'):
                if file.is_file():
                    self.assertEqual(file.read_bytes(), (path/'second'/file.relative_to(path/'first')).read_bytes())
            with self.assertRaisesRegex(ValueError, 'already exists'):
                build(path / 'first')

    def test_fallthrough_is_explicitly_reported(self):
        image = assemble(HEADER + 'WAIT cycles=0\n')
        self.assertEqual(image['schedule']['status'], 'FALLTHROUGH_FAULT')
        self.assertIn('faults', image['warnings'][0])


if __name__ == '__main__':
    unittest.main()
