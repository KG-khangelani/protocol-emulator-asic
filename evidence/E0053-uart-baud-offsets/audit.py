# SPDX-License-Identifier: Apache-2.0
"""Replay the raw E0053 board terminals and challenge the digital checks offline."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from experiments.remote_uart.check import check, require
from experiments.remote_uart.margin_check import check_margin
from tools.cold_load import UART_BINARY
from tools.production_sram import verify

SOURCE = 'ae65c0e4be8f4c110a964278b2e79aaa4499aa69'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob(path):
    return subprocess.check_output(['git', 'show', SOURCE + ':' + path], cwd=ROOT)


def board_payload(margin):
    raw = gzip.decompress(blob('evidence/E0050-powered-cold-loader/uart-transcript.json.gz'))
    require(digest(raw) == 'c660d0d69282094b6999c4b5ce83303e77c0307be5571762ec64ebb7ffb0a188',
            'cold-load provenance differs')
    rows = json.loads(raw)['loader']
    steps = [(r['ui_in'], r['rst_n'], r['raw'] if r['host_drives_uio'] else -1,
              r['expected'].get('uo_out', -1), r['expected'].get('uio_out', -1)) for r in rows]
    code = ('STEPS = ' + repr(steps) + '\n').encode() + blob('experiments/remote_uart/on_board.py')
    if margin:
        return (code + b'\n' + blob('experiments/remote_uart/baud_margin.py') +
                b'\nrun_suite(margin_trials, (project_clock, serial_peer, pad_sampler, count_clock), 3)\n')
    return code + b'\nrun_suite(delivery_trials, (wire_pair, count_clock), 2)\n'


def board_record(folder, board, margin):
    receipt = json.loads(gzip.decompress((folder / 'result.json.gz').read_bytes()))
    raw = gzip.decompress((folder / 'terminal.bin.gz').read_bytes())
    require(raw.startswith(b'OK') and raw.endswith(b'\x04>'), 'incomplete raw terminal')
    stdout, stderr = raw[2:-2].split(b'\x04', 1)
    records = [json.loads(line[8:]) for line in stdout.splitlines() if line.startswith(b'UARTLAB ')]
    require(not stderr and records == receipt['observations'], 'terminal and receipt disagree')
    require(receipt['board'] == board and receipt['source_commit'] == SOURCE
            and receipt['controller_sha256'] == digest(blob('experiments/remote_uart/run.py'))
            and receipt['board_code_sha256'] == digest(board_payload(margin)), 'source or board differs')
    original = ROOT / 'evidence/E0052-remote-uart' / board.replace('fpga-', 'board-') / 'result.json'
    baseline = json.loads(original.read_bytes())
    require(receipt['board_identity_sha256'] == baseline['board_identity_sha256']
            and receipt['websocket_wheel_sha256'] == baseline['websocket_wheel_sha256']
            and receipt['production_profile_sha256'] == verify(ROOT)['profile_sha256'],
            'fixture, dependency or production profile differs')
    image = (ROOT / 'evidence/E0051-fabricfox-uart/fabricfox-v2-12p5mhz.bin').read_bytes()
    before, upload = receipt['before'], receipt['upload']
    require(before['reachable'] and before['present'] and before['clients'] == 0 and before['kind'] == 'fpga',
            'board was offline or occupied')
    require(receipt['image_sha256'] == baseline['image_sha256'] == digest(image)
            and receipt['uart_sha256'] == UART_BINARY and not upload['evicted']
            and upload['size'] == len(image) and upload['name'] == receipt['enable']['enabled'],
            'different upload or program')
    if margin:
        decoded = check_margin(records, UART_BINARY)
        require(decoded == receipt['digital_capture_summary']
                and receipt['status'] == 'PASS_REMOTE_UART_BAUD_OFFSETS', 'derived waveforms disagree')
    else:
        check(records, UART_BINARY)
        require(receipt['status'] == 'PASS_REMOTE_UART_DIGITAL', 'original suite failed')
    return receipt


def challenge(records, name, replacements, diagnostic):
    changed = list(records)
    idx = next(i for i, r in enumerate(records) if r.get('event') == 'margin' and r['case'] == name)
    changed[idx] = dict(records[idx], **replacements)
    try:
        check_margin(changed, UART_BINARY)
    except ValueError as error:
        require(diagnostic in str(error), 'unexpected reason for rejection: ' + str(error))
    else:
        raise ValueError('altered observation escaped: ' + diagnostic)


def falsify(records):
    target = next(r for r in records if r.get('case') == 'fast-0' and r['event'] == 'margin')
    packed = bytearray.fromhex(target['samples_hex'])
    packed[-2] ^= 4  # One-sample glitch in the idle tail.
    challenge(records, 'fast-0', {'samples_hex': packed.hex()}, 'extra physical pad transition')
    # At 342 us a host meets the nominal limit but misses the derived fast-case deadline.
    challenge(records, 'fast-0', {'service_upper_us': 342, 'max_poll_gap_us': 340-target['max_read_sequence_us']},
              'missed rate-specific service deadline')
    challenge(records, 'fast-0', {'accepted': [0xaa, 0xaa]}, 'wrong FPGA delivery')
    challenge(records, 'fast-4', {'samples_hex': target['samples_hex']}, 'launch delay invisible')


def main():
    first = board_record(HERE / 'board-1', 'fpga-1', True)
    second = board_record(HERE / 'board-4', 'fpga-4', True)
    require(first['board_identity_sha256'] != second['board_identity_sha256'], 'same physical device')
    board_record(HERE / 'original-suite', 'fpga-1', False)
    falsify(first['observations'])
    trials = [r for result in (first, second) for r in result['observations'] if r.get('event') == 'margin']
    samples = sum(4*len(r['samples_hex']) for r in trials)
    print('PASS', len(trials), 'trials,', samples, 'digital samples,',
          max(r['service_upper_us'] for r in trials), 'us max host bound, four altered records rejected')


if __name__ == '__main__':
    main()
